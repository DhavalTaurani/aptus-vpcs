# -*- coding: utf-8 -*-

import json
import logging
import base64
import zipfile
import io
from datetime import timedelta, datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Fallback if dateutil is not available
    relativedelta = None

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    """Extend project.project to integrate with Odoo 17 standard template system"""

    _inherit = "project.project"

    # Construction-specific template fields
    construction_template_id = fields.Many2one(
        "construction.project.template",
        string="Construction Template",
        help="Construction-specific template for BOQ items, cost codes, and construction workflows",
    )
    is_construction = fields.Boolean(
        "Construction Project",
        default=False,
        help="Check if this is a construction project with BOQ and cost code management",
    )

    def copy(self, default=None):
        """Override copy to maintain construction template integration"""
        if default is None:
            default = {}

        # Maintain construction template reference
        if self.construction_template_id and not default.get(
            "construction_template_id"
        ):
            default["construction_template_id"] = self.construction_template_id.id

        # Apply construction template after standard copy
        project = super().copy(default)

        # If this project has a construction template, apply it
        if project.construction_template_id and project.is_construction:
            # Clear any tasks copied from the standard base template to avoid duplication.
            # The construction template is the single source of truth for tasks.
            project.task_ids.unlink()

            project.construction_template_id._apply_construction_template(project)

        return project

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to apply construction template when project is created (Odoo 18 compatible)"""
        projects = super().create(vals_list)
        for project in projects:
            # If construction template is specified, apply it
            if project.construction_template_id and project.is_construction:
                # Clear any tasks that might have been created by standard Odoo logic
                # (e.g., from a base template) to avoid duplication.
                project.task_ids.unlink()
                project.construction_template_id._apply_construction_template(project)
        return projects

    def write(self, vals):
        """Override write to apply construction template when it's assigned"""
        result = super().write(vals)

        # If construction template was just assigned, apply it
        if "construction_template_id" in vals and vals["construction_template_id"]:
            for project in self:
                if project.construction_template_id and project.is_construction:
                    # Check if template hasn't been applied yet (no construction tasks)
                    existing_construction_tasks = project.task_ids.filtered(
                        "is_boq_item"
                    )
                    if not existing_construction_tasks:
                        project.construction_template_id._apply_construction_template(
                            project, "auto_rename"
                        )
                    else:
                        # Template being applied to project with existing BOQ items
                        # Use auto_rename to avoid conflicts
                        project.construction_template_id._apply_construction_template(
                            project, "auto_rename"
                        )

        return result


class ConstructionProjectTemplate(models.Model):
    """Construction-specific project template that integrates with Odoo 17 standard project templates"""

    _name = "construction.project.template"
    _description = "Construction Project Template"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    name = fields.Char(
        "Template Name",
        required=True,
        tracking=True,
        index=True,
        help="Name of the construction project template",
    )
    description = fields.Text(
        "Description",
        tracking=True,
        help="Detailed description of the template and its intended use",
    )
    sequence = fields.Integer(
        "Sequence", default=10, help="Sequence order for template display"
    )
    active = fields.Boolean(
        "Active",
        default=True,
        tracking=True,
        help="Uncheck to archive the template without deleting it",
    )

    # Link to standard Odoo project template
    project_template_id = fields.Many2one(
        "project.project",
        string="Base Project Template",
        help="Standard Odoo project template that will be used as base for construction projects",
    )

    # Enhanced construction categorization
    construction_category = fields.Selection(
        [
            ("elv", "Extra Low Voltage (ELV)"),
            ("mep", "Mechanical, Electrical & Plumbing (MEP)"),
            ("civil", "Civil Works"),
            ("general", "General Construction"),
        ],
        string="Construction Category",
        required=True,
        tracking=True,
        index=True,
    )

    # Template versioning and approval workflow
    version = fields.Char(
        "Version",
        default="1.0",
        required=True,
        tracking=True,
        help="Template version following semantic versioning (e.g., 1.0, 1.2.3)",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "Under Review"),
            ("approved", "Approved"),
            ("archived", "Archived"),
        ],
        string="State",
        default="draft",
        tracking=True,
        index=True,
    )

    # Approval workflow fields
    approved_by = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
        help="User who approved this template",
    )
    approved_date = fields.Datetime(
        "Approved Date",
        readonly=True,
        help="Date and time when the template was approved",
    )
    review_notes = fields.Text(
        "Review Notes",
        help="Notes from the review process, including feedback and comments",
    )

    # Template relationships
    task_template_ids = fields.One2many(
        "construction.task.template", "template_id", string="Task Templates"
    )
    boq_template_ids = fields.One2many(
        "construction.boq.template", "template_id", string="BOQ Item Templates"
    )
    cost_estimation_ids = fields.One2many(
        "construction.cost.estimation.template",
        "template_id",
        string="Cost Estimation Templates",
    )
    milestone_template_ids = fields.One2many(
        "construction.milestone.template", "template_id", string="Milestone Templates"
    )

    # Template statistics
    usage_count = fields.Integer(
        "Usage Count",
        compute="_compute_usage_count",
        help="Number of projects created using this template",
    )
    last_used_date = fields.Datetime(
        "Last Used Date", compute="_compute_last_used_date"
    )

    # Company support
    company_id = fields.Many2one(
        "res.company", "Company", default=lambda self: self.env.company
    )

    # Template data structure (JSON field for flexibility)
    template_data = fields.Text(
        "Template Data Structure",
        help="JSON structure containing template configuration",
    )

    # Reset to draft availability
    can_reset_to_draft_computed = fields.Boolean(
        "Can Reset to Draft",
        compute="_compute_can_reset_to_draft",
        help="Indicates if the template can be reset to draft state",
    )

    # Computed fields
    @api.depends("project_template_id")
    def _compute_usage_count(self):
        """Compute how many times this template has been used"""
        for template in self:
            # Count projects created from this template
            project_count = self.env["project.project"].search_count(
                [("construction_template_id", "=", template.id)]
            )
            template.usage_count = project_count

    @api.depends("project_template_id")
    def _compute_last_used_date(self):
        """Compute when this template was last used"""
        for template in self:
            last_project = self.env["project.project"].search(
                [("construction_template_id", "=", template.id)],
                order="create_date desc",
                limit=1,
            )
            template.last_used_date = (
                last_project.create_date if last_project else False
            )

    @api.depends("state")
    def _compute_can_reset_to_draft(self):
        """Compute if template can be reset to draft"""
        for template in self:
            template.can_reset_to_draft_computed = template.can_reset_to_draft()

    # SQL constraints
    _version_not_empty = models.Constraint(
        "CHECK(LENGTH(TRIM(version)) > 0)",
        "Version cannot be empty!",
    )
    
    _sequence_positive = models.Constraint(
        "CHECK(sequence >= 0)",
        "Sequence must be positive!",
    )
    
    _name_company_unique = models.Constraint(
        "UNIQUE(name, company_id)",
        "Template name must be unique per company!",
    )

    # Template validation and integrity checks
    @api.constrains("task_template_ids", "boq_template_ids")
    def _check_template_integrity(self):
        """Validate template data integrity"""
        for template in self:
            # Check for circular dependencies in task hierarchy
            # template._check_task_hierarchy_integrity()

            # Validate BOQ code uniqueness within template
            # template._check_boq_code_uniqueness()

            # Validate cost estimation completeness
            template._check_cost_estimation_completeness()

            # Validate milestone dependencies
            # template._check_milestone_dependencies()

    @api.constrains("state", "task_template_ids")
    def _check_approval_requirements(self):
        """Check requirements before template approval"""
        for template in self:
            if template.state == "approved":
                # Must have at least one task template
                if not template.task_template_ids:
                    raise ValidationError(
                        _("Template '%s' cannot be approved without task templates.")
                        % template.name
                    )

                # Validate cost estimation coverage
                if not template.cost_estimation_ids:
                    raise ValidationError(
                        _("Template '%s' must have cost estimations before approval.")
                        % template.name
                    )

    @api.constrains("version")
    def _check_version_format(self):
        """Validate version format (semantic versioning)"""
        import re

        version_pattern = r"^\d+\.\d+(\.\d+)?(-[a-zA-Z0-9]+)?$"

        for template in self:
            if template.version and not re.match(version_pattern, template.version):
                raise ValidationError(
                    _(
                        "Version '%s' must follow semantic versioning format (e.g., 1.0, 1.2.3, 2.0-beta)"
                    )
                    % template.version
                )

    @api.constrains("template_data")
    def _check_template_data_format(self):
        """Validate JSON template data format"""
        for template in self:
            if template.template_data:
                try:
                    data = json.loads(template.template_data)
                    # Validate required structure
                    required_keys = ["version", "category", "structure"]
                    for key in required_keys:
                        if key not in data:
                            raise ValidationError(
                                _("Template data must contain '%s' key") % key
                            )
                except (json.JSONDecodeError, ValueError) as e:
                    raise ValidationError(
                        _("Invalid JSON format in template data: %s") % str(e)
                    )

    def _check_task_hierarchy_integrity(self):
        """Check for circular dependencies and proper hierarchy"""
        self.ensure_one()

        def check_circular_dependency(task, visited=None):
            if visited is None:
                visited = set()

            if task.id in visited:
                raise ValidationError(
                    _(
                        "Circular dependency detected in task hierarchy for template '%s'"
                    )
                    % self.name
                )

            visited.add(task.id)
            if task.parent_template_id:
                check_circular_dependency(task.parent_template_id, visited.copy())

        for task in self.task_template_ids:
            if task.parent_template_id:
                check_circular_dependency(task)

        # Validate hierarchy levels
        hierarchy_levels = ["project", "phase", "work_package"]
        for task in self.task_template_ids:
            if task.parent_template_id:
                parent_level_idx = hierarchy_levels.index(
                    task.parent_template_id.hierarchy_level
                )
                child_level_idx = hierarchy_levels.index(task.hierarchy_level)

                if child_level_idx <= parent_level_idx:
                    raise ValidationError(
                        _(
                            "Task '%s' hierarchy level must be lower than its parent '%s'"
                        )
                        % (task.name, task.parent_template_id.name)
                    )

    def _check_boq_code_uniqueness(self):
        """Ensure BOQ codes are unique within template"""
        self.ensure_one()

        boq_codes = []
        for task in self.task_template_ids.filtered("is_boq_item"):
            if task.boq_code:
                if task.boq_code in boq_codes:
                    raise ValidationError(
                        _("BOQ code '%s' is duplicated in template '%s'")
                        % (task.boq_code, self.name)
                    )
                boq_codes.append(task.boq_code)

        for boq in self.boq_template_ids:
            if boq.code in boq_codes:
                raise ValidationError(
                    _("BOQ code '%s' is duplicated in template '%s'")
                    % (boq.code, self.name)
                )
            boq_codes.append(boq.code)

    def _check_cost_estimation_completeness(self):
        """Validate cost estimation covers all categories"""
        self.ensure_one()

        if not self.cost_estimation_ids:
            return  # Skip if no cost estimations

        # Check if all major cost categories are covered
        covered_categories = set(self.cost_estimation_ids.mapped("cost_category"))
        required_categories = {"material", "labour"}  # Minimum required categories

        missing_categories = required_categories - covered_categories
        if missing_categories:
            raise ValidationError(
                _("Template '%s' is missing cost estimations for categories: %s")
                % (self.name, ", ".join(missing_categories))
            )

    def _check_milestone_dependencies(self):
        """Validate milestone dependencies and payment percentages"""
        self.ensure_one()

        payment_milestones = self.milestone_template_ids.filtered(
            "is_payment_milestone"
        )
        if payment_milestones:
            total_payment_percentage = sum(
                payment_milestones.mapped("payment_percentage")
            )

            if total_payment_percentage > 100:
                raise ValidationError(
                    _("Total payment percentage (%s%%) exceeds 100%% in template '%s'")
                    % (total_payment_percentage, self.name)
                )

            # Check for reasonable payment distribution
            if total_payment_percentage < 90:
                _logger.warning(
                    "Template '%s' has payment milestones totaling only %s%%. Consider reviewing payment structure.",
                    self.name,
                    total_payment_percentage,
                )

    def _apply_construction_template(self, project, conflict_resolution="auto_rename"):
        """Apply construction template to a project - creates BOQ structure and tasks

        Args:
            project: Project to apply template to
            conflict_resolution: How to handle BOQ code conflicts
                - 'auto_rename': Automatically rename conflicting codes (default)
                - 'skip_existing': Skip items with conflicting codes
                - 'replace_existing': Replace existing items with template items
        """
        self.ensure_one()
        project.ensure_one()

        if not self.state == "approved":
            _logger.warning(
                "Applying non-approved template '%s' to project '%s'",
                self.name,
                project.name,
            )

        try:
            # Apply template in sequence to maintain data integrity
            # ONLY apply task templates (which include BOQ items) - NO SEPARATE BOQ CREATION
            self._apply_template_tasks(project, conflict_resolution)

            # Apply dynamic milestones based on payment terms if available
            self._apply_dynamic_milestones(project)

            # Apply cost estimations (not BOQ items)
            self._apply_template_cost_estimations(project)

            # The recursive call that was here has been removed.
            # project.construction_template_id = self.id

            _logger.info(
                "Successfully applied construction template '%s' to project '%s'",
                self.name,
                project.name,
            )

        except Exception as e:
            _logger.error(
                "Failed to apply construction template '%s' to project '%s': %s",
                self.name,
                project.name,
                str(e),
            )
            raise

    def _apply_template_tasks(self, project, conflict_resolution="auto_rename"):
        """Apply task templates to project with proper hierarchy"""
        self.ensure_one()

        # Create tasks in hierarchy order (project -> phase -> work_package)
        task_mapping = {}  # Map template task ID to created task ID
        boq_task_count = 0  # Track BOQ items created

        # OPTIMIZATION: Get all existing BOQ codes in one query to avoid multiple database hits
        existing_boq_codes = set()
        if conflict_resolution in ["auto_rename", "skip_existing"]:
            existing_tasks = self.env["project.task"].search(
                [
                    ("project_id", "=", project.id),
                    ("is_boq_item", "=", True),
                    ("boq_code", "!=", False),
                ]
            )
            existing_boq_codes = set(existing_tasks.mapped("boq_code"))

        # Sort tasks by hierarchy level and sequence
        hierarchy_order = ["project", "phase", "work_package"]
        sorted_tasks = self.task_template_ids.sorted(
            key=lambda t: (hierarchy_order.index(t.hierarchy_level), t.sequence, t.id)
        )
        for task_template in sorted_tasks:
            # Handle BOQ code conflicts using the optimized single-query approach
            boq_code = task_template.boq_code
            if task_template.is_boq_item and boq_code:
                boq_code = self._resolve_boq_code_conflict_optimized(
                    boq_code,
                    existing_boq_codes,
                    conflict_resolution,
                    project.name,
                )
                # Skip this task if conflict resolution returned None
                if boq_code is None:
                    continue

            # Prepare task values
            task_vals = {
                "name": task_template.name,
                "description": task_template.description,
                "project_id": project.id,
                "sequence": task_template.sequence,
                "is_boq_item": task_template.is_boq_item,
                "boq_code": boq_code,
                "estimated_quantity": task_template.estimated_quantity,
                "unit_cost": task_template.unit_cost,
                "unit_of_measure_id": (
                    task_template.unit_of_measure_id.id
                    if task_template.unit_of_measure_id
                    else False
                ),
                "cost_code_id": (
                    task_template.cost_code_id.id
                    if task_template.cost_code_id
                    else False
                ),
            }

            # Set parent task if exists
            if (
                task_template.parent_template_id
                and task_template.parent_template_id.id in task_mapping
            ):
                task_vals["parent_id"] = task_mapping[
                    task_template.parent_template_id.id
                ]

            # Create task
            task = self.env["project.task"].create(task_vals)
            task_mapping[task_template.id] = task.id

            # Count BOQ items
            if task_template.is_boq_item:
                boq_task_count += 1

            _logger.debug(
                "Created task '%s' (BOQ: %s) in project '%s'",
                task.name,
                task.is_boq_item,
                project.name,
            )

        # Log BOQ task creation summary
        _logger.info(
            "Created %d BOQ tasks from template '%s' for project '%s'",
            boq_task_count,
            self.name,
            project.name,
        )

        # Log template-specific BOQ count (dynamic based on template configuration)
        expected_boq_count = len(self.task_template_ids.filtered("is_boq_item"))
        if boq_task_count != expected_boq_count:
            _logger.warning(
                "Template '%s' created %d BOQ tasks, expected %d based on template configuration. Please review template data.",
                self.name,
                boq_task_count,
                expected_boq_count,
            )

    # NOTE: _apply_template_boq_items method removed to prevent duplication
    # BOQ items are now created ONLY through task templates with is_boq_item=True
    # This eliminates the duplication issue where BOQ items were created twice

    def _apply_template_boq_items(self, project):
        """
        PROBE METHOD: This method is intentionally left empty.
        It is suspected that another part of the module is calling this method,
        causing duplicate BOQ items. If the warning below appears in the logs,
        this theory is confirmed.
        """
        _logger.warning(
            "DEPRECATED METHOD CALLED: _apply_template_boq_items was called for template '%s' on project '%s'. "
            "This is the source of the duplicate BOQ items. This method should not be used.",
            self.name,
            project.name,
        )
        return True

    def _apply_dynamic_milestones(self, project):
        """Apply dynamic milestones - integration handled by progressive payment module if available"""
        self.ensure_one()

        # Check if project has sale order
        sale_order = (
            project.sale_order_id or project.sale_line_id.order_id
            if project.sale_line_id
            else False
        )

        # Check if progressive payment module is available and has created milestones
        dynamic_milestones_created = False
        if sale_order:
            try:
                # Check if progressive payment module has already created milestones
                # The progressive payment module should extend this method to create milestones
                # Use hasattr to safely check if payment_milestone_id field exists
                if hasattr(self.env["project.task"], "payment_milestone_id"):
                    existing_payment_milestones = project.task_ids.filtered(
                        "payment_milestone_id"
                    )
                    if existing_payment_milestones:
                        dynamic_milestones_created = True
                        _logger.info(
                            "Found %d dynamic milestones created by progressive payment module for project '%s'",
                            len(existing_payment_milestones),
                            project.name,
                        )
            except Exception as e:
                _logger.debug(
                    "Error checking for dynamic milestones in project '%s': %s",
                    project.name,
                    str(e),
                )
            if not dynamic_milestones_created:
                # Fallback to template milestones if no dynamic milestones were created
                _logger.info(
                    "No dynamic milestones found for project '%s', using template milestones",
                    project.name,
                )
                self._apply_template_milestones(project)

    def _apply_template_milestones(self, project):
        """Apply milestone templates to project (fallback method)"""
        self.ensure_one()

        for milestone_template in self.milestone_template_ids:
            # Calculate planned date
            planned_date = False
            if project.date_start:
                from dateutil.relativedelta import relativedelta

                planned_date = project.date_start + relativedelta(
                    days=milestone_template.days_from_start
                )

            # Create project milestone as a task with milestone naming convention
            milestone_vals = {
                "name": f"🎯 {milestone_template.name}",
                "description": milestone_template.description,
                "project_id": project.id,
                "sequence": 999,  # Put milestones at the end
                "date_deadline": planned_date,  # Use deadline for milestone date
            }

            milestone_task = self.env["project.task"].create(milestone_vals)

            _logger.debug(
                "Created template milestone '%s' in project '%s'",
                milestone_template.name,
                project.name,
            )

    def _apply_template_cost_estimations(self, project):
        """Apply cost estimation templates to project"""
        self.ensure_one()

        # This would integrate with project budgeting
        # For now, we'll log the cost estimations
        total_estimated_cost = sum(self.cost_estimation_ids.mapped("estimated_cost"))

        if total_estimated_cost > 0:
            _logger.info(
                "Applied cost estimations totaling %s to project '%s'",
                total_estimated_cost,
                project.name,
            )

    @api.model
    def validate_template_performance(self, template_id):
        """Validate template performance based on historical data"""
        template = self.browse(template_id)
        if not template.exists():
            return False

        # Get projects created from this template
        projects = self.env["project.project"].search(
            [
                ("construction_template_id", "=", template_id),
                ("stage_id.name", "in", ["Completed", "Cancelled"]),
            ]
        )

        if not projects:
            return True  # No historical data to validate against

        # Calculate performance metrics
        total_projects = len(projects)
        completed_projects = projects.filtered(lambda p: p.stage_id.name == "Completed")
        success_rate = len(completed_projects) / total_projects * 100

        # Update template performance data
        if success_rate < 70:  # Less than 70% success rate
            _logger.warning(
                "Template '%s' has low success rate (%s%%). Consider reviewing template structure.",
                template.name,
                success_rate,
            )

        return success_rate >= 50  # Minimum 50% success rate for validation

    def _resolve_boq_code_conflict_optimized(
        self,
        original_code,
        existing_boq_codes,
        conflict_resolution,
        project_name,
    ):
        """Optimized BOQ code conflict resolution using single query and in-memory processing"""
        if not original_code:
            return original_code

        # If code doesn't exist, use it and add to the set of used codes
        if original_code not in existing_boq_codes:
            existing_boq_codes.add(original_code)
            return original_code

        # Handle conflict based on strategy
        if conflict_resolution == "skip_existing":
            _logger.info(
                "Skipping BOQ item with code '%s' - already exists in project '%s'",
                original_code,
                project_name,
            )
            return None

        elif conflict_resolution == "replace_existing":
            # For replace_existing, we would need to handle task deletion separately
            # For now, log and use original code (task deletion handled elsewhere)
            _logger.info(
                "Replacing existing BOQ item with code '%s' in project '%s'",
                original_code,
                project_name,
            )
            return original_code

        else:  # auto_rename (default)
            # Generate unique code using in-memory check (no database queries)
            counter = 1
            new_code = f"{original_code}-{counter:03d}"

            # Check against the growing set of existing codes
            while new_code in existing_boq_codes:
                counter += 1
                new_code = f"{original_code}-{counter:03d}"

            # Add the new unique code to the set
            existing_boq_codes.add(new_code)

            _logger.warning(
                "BOQ code conflict resolved: '%s' changed to '%s' in project '%s'",
                original_code,
                new_code,
                project_name,
            )

            return new_code

    # NOTE: Legacy _resolve_boq_code_conflict method removed
    # Now using _resolve_boq_code_conflict_optimized for better performance
    # Single query approach with in-memory processing eliminates multiple database hits

    def create_version_backup(self, change_log=None):
        """Create a version backup of the current template"""
        self.ensure_one()

        # Generate new version number
        existing_versions = self.env["construction.template.version"].search(
            [("template_id", "=", self.id)], order="version desc"
        )

        if existing_versions:
            # Parse latest version and increment
            latest_version = existing_versions[0].version
            try:
                major, minor = latest_version.split(".")[:2]
                new_version = f"{major}.{int(minor) + 1}"
            except (ValueError, IndexError):
                new_version = f"{latest_version}_1"
        else:
            new_version = "1.0"

        # Create version record
        version = self.env["construction.template.version"].create(
            {
                "template_id": self.id,
                "version": new_version,
                "state": "draft",
                "change_log": change_log
                or f"Backup created on {fields.Datetime.now()}",
                "previous_version_id": (
                    existing_versions[0].id if existing_versions else False
                ),
            }
        )

        # Create backup data
        version.create_backup()

        # Update template version
        self.version = new_version

        return version

    def restore_from_backup(self, version_id):
        """Restore template from backup version"""
        self.ensure_one()

        version = self.env["construction.template.version"].browse(version_id)
        if not version.exists() or version.template_id != self:
            raise UserError(_("Invalid backup version selected."))

        if not version.template_backup_data:
            raise UserError(_("No backup data available for this version."))

        # Create current backup before restore
        self.create_version_backup(
            f"Backup before restore to version {version.version}"
        )

        # Restore from backup data
        backup_data = json.loads(version.template_backup_data)

        # Update template data
        template_data = backup_data.get("template", {})
        self.write(
            {
                "name": template_data.get("name", self.name),
                "description": template_data.get("description", self.description),
                "template_data": template_data.get("template_data", self.template_data),
            }
        )

        # Clear existing related records
        self.task_template_ids.unlink()
        self.boq_template_ids.unlink()
        # self.milestone_template_ids.unlink()
        self.cost_estimation_ids.unlink()

        # Restore related records
        self._restore_task_templates(backup_data.get("tasks", []))
        self._restore_boq_templates(backup_data.get("boq_items", []))
        self._restore_milestone_templates(backup_data.get("milestones", []))
        self._restore_cost_estimation_templates(backup_data.get("cost_estimations", []))

        return True

    def _restore_task_templates(self, tasks_data):
        """Restore task templates from backup data"""
        task_mapping = {}

        # Create tasks first (without parent relationships)
        for task_data in tasks_data:
            task = self.env["construction.task.template"].create(
                {
                    "template_id": self.id,
                    "name": task_data.get("name"),
                    "description": task_data.get("description"),
                    "sequence": task_data.get("sequence", 10),
                    "hierarchy_level": task_data.get("hierarchy_level", "work_package"),
                    "is_boq_item": task_data.get("is_boq_item", False),
                    "boq_code": task_data.get("boq_code"),
                    "estimated_quantity": task_data.get("estimated_quantity", 1.0),
                    "unit_cost": task_data.get("unit_cost", 0.0),
                }
            )
            task_mapping[task_data.get("id")] = task

        # Set parent relationships
        for task_data in tasks_data:
            if task_data.get("parent_template_id"):
                parent_task = task_mapping.get(task_data["parent_template_id"])
                if parent_task:
                    task_mapping[task_data.get("id")].parent_template_id = (
                        parent_task.id
                    )

    def _restore_boq_templates(self, boq_data):
        """Restore BOQ templates from backup data"""
        for boq_item in boq_data:
            self.env["construction.boq.template"].create(
                {
                    "template_id": self.id,
                    "name": boq_item.get("name"),
                    "code": boq_item.get("code"),
                    "description": boq_item.get("description"),
                    "quantity": boq_item.get("quantity", 1.0),
                    "unit_cost": boq_item.get("unit_cost", 0.0),
                    "sequence": boq_item.get("sequence", 10),
                    "unit_of_measure_id": self.env.ref("uom.product_uom_unit").id,
                }
            )

    def _restore_milestone_templates(self, milestone_data):
        """Restore milestone templates from backup data"""
        for milestone in milestone_data:
            self.env["construction.milestone.template"].create(
                {
                    "template_id": self.id,
                    "name": milestone.get("name"),
                    "description": milestone.get("description"),
                    "milestone_type": milestone.get(
                        "milestone_type", "phase_completion"
                    ),
                    "days_from_start": milestone.get("days_from_start", 0),
                    "is_payment_milestone": milestone.get(
                        "is_payment_milestone", False
                    ),
                    "payment_percentage": milestone.get("payment_percentage", 0.0),
                }
            )

    def _restore_cost_estimation_templates(self, cost_data):
        """Restore cost estimation templates from backup data"""
        for cost_item in cost_data:
            self.env["construction.cost.estimation.template"].create(
                {
                    "template_id": self.id,
                    "name": cost_item.get("name"),
                    "description": cost_item.get("description"),
                    "cost_category": cost_item.get("cost_category", "material"),
                    "estimated_cost": cost_item.get("estimated_cost", 0.0),
                    "contingency_percentage": cost_item.get(
                        "contingency_percentage", 10.0
                    ),
                }
            )

    @api.model
    def _cron_create_template_backups(self):
        """Cron method to create automated backups for approved templates"""
        try:
            # Get approved templates
            templates = self.search([("state", "=", "approved")])

            for template in templates:
                try:
                    # Check if template has been modified since last backup
                    latest_version = self.env["construction.template.version"].search(
                        [("template_id", "=", template.id)],
                        order="created_date desc",
                        limit=1,
                    )

                    if not latest_version or (
                        template.write_date
                        and latest_version.created_date < template.write_date
                    ):
                        template.create_version_backup("Automated backup")
                except Exception as e:
                    _logger.error(
                        f"Failed to create backup for template {template.name}: {str(e)}"
                    )
        except Exception as e:
            _logger.error(f"Failed to run template backup process: {str(e)}")

    @api.model
    def _cron_cleanup_old_backups(self):
        """Cron method to cleanup old backup versions"""
        try:
            cleaned_count = self.cleanup_old_backups(retention_days=365)
            _logger.info(
                f"Template backup cleanup completed: {cleaned_count} old versions removed"
            )
        except Exception as e:
            _logger.error(f"Failed to cleanup old template backups: {str(e)}")

    @api.model
    def cleanup_old_backups(self, retention_days=365):
        """Clean up old backup versions based on retention policy"""
        cutoff_date = fields.Date.today() - timedelta(days=retention_days)

        old_versions = self.env["construction.template.version"].search(
            [
                ("created_date", "<", cutoff_date),
                ("state", "=", "archived"),
            ]
        )

        _logger.info(f"Cleaning up {len(old_versions)} old template versions")
        old_versions.unlink()

        return len(old_versions)

    @api.model
    def _cron_create_template_backups(self):
        """Cron job to create automated template backups"""
        templates = self.search([("state", "=", "approved")])
        backup_count = 0

        for template in templates:
            # Check if template has been modified since last backup
            latest_version = self.env["construction.template.version"].search(
                [("template_id", "=", template.id)], order="created_date desc", limit=1
            )

            if not latest_version or (
                template.write_date
                and latest_version.created_date < template.write_date
            ):
                template.create_version_backup("Automated backup")
                backup_count += 1

        _logger.info(f"Created {backup_count} automated template backups")
        return backup_count

    @api.model
    def _cron_cleanup_old_backups(self):
        """Cron job to cleanup old template backups"""
        return self.cleanup_old_backups(retention_days=365)

    @api.model
    def _cron_create_template_backups(self):
        """Cron job to create automated template backups"""
        templates = self.search([("state", "=", "approved")])
        for template in templates:
            # Check if template has been modified since last backup
            latest_version = self.env["construction.template.version"].search(
                [("template_id", "=", template.id)], order="created_date desc", limit=1
            )

            if not latest_version or (
                template.write_date
                and latest_version.created_date < template.write_date
            ):
                template.create_version_backup("Automated backup")

    @api.model
    def _cron_cleanup_old_backups(self):
        """Cron job to cleanup old template backups"""
        return self.cleanup_old_backups(retention_days=365)

    # Template approval workflow with email notifications
    def action_submit_for_review(self):
        """Submit template for review"""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft templates can be submitted for review."))

        # Validate template before submission
        self._validate_template_for_review()

        # Create version backup
        self.create_version_backup("Submitted for review")

        # Update state
        self.state = "review"

        # Send notification to reviewers
        self._send_review_notification()

        # Log activity
        self.activity_schedule(
            "construction_management.mail_activity_template_review",
            summary=f"Template '{self.name}' submitted for review",
            note=f"Template version {self.version} has been submitted for review.",
            user_id=self._get_reviewer_user().id,
        )

    def action_approve_template(self):
        """Approve template"""
        self.ensure_one()
        if self.state != "review":
            raise UserError(_("Only templates under review can be approved."))

        # Check user permissions
        if not self.env.user.has_group(
            "construction_management.group_construction_template_manager"
        ):
            raise UserError(_("You don't have permission to approve templates."))

        # Update approval fields
        self.write(
            {
                "state": "approved",
                "approved_by": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            }
        )

        # Create approved version
        version = self.env["construction.template.version"].search(
            [
                ("template_id", "=", self.id),
                ("version", "=", self.version),
            ],
            limit=1,
        )

        if version:
            version.action_approve()

        # Send approval notification
        self._send_approval_notification()

        # Complete review activity
        self.activity_unlink(["construction_management.mail_activity_template_review"])

    def action_reject_template(self, rejection_reason=None):
        """Reject template"""
        self.ensure_one()
        if self.state != "review":
            raise UserError(_("Only templates under review can be rejected."))

        # Check user permissions
        if not self.env.user.has_group(
            "construction_management.group_construction_template_manager"
        ):
            raise UserError(_("You don't have permission to reject templates."))

        # Update state and add rejection note
        self.write(
            {
                "state": "draft",
                "review_notes": rejection_reason or "Template rejected for review.",
            }
        )

        # Send rejection notification
        self._send_rejection_notification(rejection_reason)

        # Complete review activity
        self.activity_unlink(["construction_management.mail_activity_template_review"])

    def action_archive_template(self):
        """Archive template"""
        self.ensure_one()
        if self.state not in ["approved", "draft"]:
            raise UserError(_("Only approved or draft templates can be archived."))

        # Create final backup
        self.create_version_backup("Template archived")

        # Update state
        self.state = "archived"
        self.active = False

        # Send archive notification
        self._send_archive_notification()

    def action_reset_to_draft(self):
        """Reset approved template back to draft for modifications"""
        self.ensure_one()

        if self.state != "approved":
            raise UserError(_("Only approved templates can be reset to draft."))

        # Check user permissions
        if not self.env.user.has_group(
            "construction_management.group_construction_template_manager"
        ):
            raise UserError(_("You don't have permission to reset templates to draft."))

        # Check if template is being used in active projects
        active_projects = self.env["project.project"].search(
            [
                ("construction_template_id", "=", self.id),
                ("stage_id.name", "not in", ["Completed", "Cancelled"]),
            ]
        )

        if active_projects:
            project_names = ", ".join(active_projects.mapped("name"))
            raise UserError(
                _(
                    "Cannot reset template to draft. It is currently being used in active projects: %s. "
                    "Please complete or cancel these projects first, or create a new template version."
                )
                % project_names
            )

        # Check if template is referenced in products
        products_using_template = self.env["product.template"].search(
            [("construction_template_id", "=", self.id)]
        )

        if products_using_template:
            product_names = ", ".join(products_using_template.mapped("name"))
            self.message_post(
                body=_(
                    "Warning: This template is referenced by products: %s. "
                    "Consider updating these products if you make significant changes."
                )
                % product_names,
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

        # Create a backup version before resetting
        backup_version = self.create_version_backup(
            f"Backup before reset to draft by {self.env.user.name} on {fields.Datetime.now()}"
        )

        # Reset approval fields and state
        self.write(
            {
                "state": "draft",
                "approved_by": False,
                "approved_date": False,
                "review_notes": f"Reset to draft from approved state by {self.env.user.name} on {fields.Datetime.now()}. "
                f"Previous version backed up as v{backup_version.version}.",
            }
        )

        # Send reset notification
        self._send_reset_notification()

        # Log the reset action
        self.message_post(
            body=_(
                "Template reset to draft state by %s. Previous approved version backed up as v%s."
            )
            % (self.env.user.name, backup_version.version),
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Template Reset"),
                "message": _(
                    "Template has been reset to draft. Previous version backed up as v%s."
                )
                % backup_version.version,
                "type": "success",
                "sticky": False,
            },
        }

    def can_reset_to_draft(self):
        """Check if template can be reset to draft"""
        self.ensure_one()

        # Must be approved
        if self.state != "approved":
            return False

        # User must have permission
        if not self.env.user.has_group(
            "construction_management.group_construction_template_manager"
        ):
            return False

        # Check for active projects using this template
        active_projects = self.env["project.project"].search(
            [
                ("construction_template_id", "=", self.id),
                ("stage_id.name", "not in", ["Completed", "Cancelled"]),
            ],
            limit=1,
        )

        return not bool(active_projects)

    def action_view_projects(self):
        """View projects created from this template"""
        self.ensure_one()
        projects = self.env["project.project"].search(
            [("construction_template_id", "=", self.id)]
        )

        action = {
            "name": _("Projects from Template: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "view_mode": "list,form",
            "domain": [("construction_template_id", "=", self.id)],
            "context": {
                "default_construction_template_id": self.id,
                "default_is_construction": True,
            },
        }

        if len(projects) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": projects.id,
                }
            )

        return action

    def _validate_template_for_review(self):
        """Validate template before submitting for review"""
        errors = []

        # Check required fields
        if not self.name:
            errors.append("Template name is required")

        if not self.description:
            errors.append("Template description is required")

        if not self.construction_category:
            errors.append("Construction category is required")

        # Check template content
        if not self.task_template_ids:
            errors.append("At least one task template is required")

        if not self.cost_estimation_ids:
            errors.append("At least one cost estimation is required")

        # Check BOQ codes for BOQ items
        boq_tasks = self.task_template_ids.filtered("is_boq_item")
        for task in boq_tasks:
            if not task.boq_code:
                errors.append(f"BOQ code is required for task '{task.name}'")

        if errors:
            raise ValidationError(
                _("Template validation failed:\n%s") % "\n".join(errors)
            )

    def _get_reviewer_user(self):
        """Get the user responsible for reviewing templates"""
        # Try to find a template manager
        template_managers = self.env.ref(
            "construction_management.group_construction_template_manager"
        ).user_ids
        if template_managers:
            return template_managers[0]

        # Fallback to admin
        return self.env.ref("base.user_admin")

    def _send_review_notification(self):
        """Send email notification for template review"""
        template = self.env.ref(
            "construction_management.email_template_review_request",
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_approval_notification(self):
        """Send email notification for template approval"""
        template = self.env.ref(
            "construction_management.email_template_approval_notification",
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_rejection_notification(self, rejection_reason=None):
        """Send email notification for template rejection"""
        template = self.env.ref(
            "construction_management.email_template_rejection_notification",
            raise_if_not_found=False,
        )
        if template:
            # Add rejection reason to context
            template = template.with_context(rejection_reason=rejection_reason)
            template.send_mail(self.id, force_send=True)

    def _send_archive_notification(self):
        """Send email notification for template archival"""
        template = self.env.ref(
            "construction_management.email_template_archive_notification",
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_reset_notification(self):
        """Send email notification for template reset to draft"""
        template = self.env.ref(
            "construction_management.email_template_reset_notification",
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def create_construction_project(self, project_vals=None):
        """Create a new construction project based on this template

        This method integrates with Odoo 17 standard sale_project flow:
        1. Uses standard project template if available
        2. Adds construction-specific features
        3. Creates BOQ items as tasks with proper hierarchy
        """
        self.ensure_one()

        if not project_vals:
            project_vals = {}

        # Set construction-specific defaults
        project_vals.update(
            {
                "name": project_vals.get("name", f"{self.name} Project"),
                "is_construction": True,
                "construction_template_id": self.id,
            }
        )

        # Create project using standard Odoo template if available
        if self.project_template_id:
            # Use standard Odoo copy mechanism
            project = self.project_template_id.copy(project_vals)
        else:
            # Create new project
            project = self.env["project.project"].create(project_vals)

        # Construction-specific features are applied via the create/copy overrides
        # of project.project, so no explicit call is needed here.

        return project


class ConstructionTaskTemplate(models.Model):
    """Construction task template with BOQ integration"""

    _name = "construction.task.template"
    _description = "Construction Task Template"
    _order = "sequence, name"

    name = fields.Char("Task Name", required=True, help="Name of the task template")
    description = fields.Text(
        "Description", help="Detailed description of the task and its requirements"
    )
    sequence = fields.Integer(
        "Sequence", default=10, help="Sequence order for task execution"
    )
    template_id = fields.Many2one(
        "construction.project.template",
        string="Construction Template",
        required=True,
        ondelete="cascade",
    )
    parent_template_id = fields.Many2one(
        "construction.task.template", string="Parent Task Template"
    )
    child_template_ids = fields.One2many(
        "construction.task.template", "parent_template_id", string="Subtask Templates"
    )

    # Task hierarchy levels
    hierarchy_level = fields.Selection(
        [
            ("project", "Project Level"),
            ("phase", "Phase Level"),
            ("work_package", "Work Package (BOQ Level)"),
        ],
        string="Hierarchy Level",
        default="work_package",
        required=True,
        help="Defines the level in the project hierarchy: Project → Phase → Work Package",
    )

    # Task stages using Odoo 17 standard task stages
    initial_stage = fields.Selection(
        [
            ("task_stage_draft", "Draft"),
            ("task_stage_approved", "Approved"),
            ("task_stage_in_progress", "In Progress"),
            ("task_stage_completed", "Completed"),
        ],
        string="Initial Stage",
        default="task_stage_draft",
        required=True,
        help="Initial stage that tasks created from this template will have",
    )

    # Construction-specific fields
    is_boq_item = fields.Boolean(
        "Is BOQ Item",
        default=False,
        help="Check if this task represents a BOQ (Bill of Quantities) item",
    )
    boq_code = fields.Char(
        "BOQ Code",
        index=True,
        help="Unique BOQ code for this item (required if BOQ item)",
    )
    estimated_quantity = fields.Float(
        "Estimated Quantity",
        default=1.0,
        help="Estimated quantity for this task/BOQ item",
    )
    unit_of_measure_id = fields.Many2one(
        "uom.uom", string="Unit of Measure", help="Unit of measure for quantities"
    )
    unit_cost = fields.Monetary(
        "Unit Cost",
        currency_field="currency_id",
        help="Cost per unit for this task/BOQ item",
    )
    currency_id = fields.Many2one(
        "res.currency", related="template_id.company_id.currency_id"
    )

    # Cost code integration
    cost_code_id = fields.Many2one("construction.cost.code", string="Cost Code")

    # Resource allocation
    resource_allocation_ids = fields.One2many(
        "construction.resource.allocation.template",
        "task_template_id",
        string="Resource Allocations",
        help="Resource allocations required for this task template",
    )

    # Milestone integration
    milestone_template_ids = fields.One2many(
        "construction.milestone.template",
        "task_template_id",
        string="Milestone Templates",
        help="Milestones associated with this task template",
    )

    @api.constrains("parent_template_id")
    def _check_parent_template(self):
        """Ensure parent template belongs to same project template"""
        for task in self:
            if (
                task.parent_template_id
                and task.parent_template_id.template_id != task.template_id
            ):
                raise ValidationError(
                    _(
                        "Parent task template must belong to the same construction template."
                    )
                )

    @api.constrains("estimated_quantity", "unit_cost")
    def _check_positive_values(self):
        """Ensure quantities and costs are positive"""
        for task in self:
            if task.estimated_quantity < 0:
                raise ValidationError(_("Estimated quantity must be positive."))
            if task.unit_cost < 0:
                raise ValidationError(_("Unit cost must be positive."))

    # SQL constraints
    _sequence_positive = models.Constraint(
        "CHECK(sequence >= 0)",
        "Sequence must be positive!",
    )
    
    _estimated_quantity_positive = models.Constraint(
        "CHECK(estimated_quantity >= 0)",
        "Estimated quantity must be positive!",
    )


class ConstructionBOQTemplate(models.Model):
    """BOQ item template for construction projects"""

    _name = "construction.boq.template"
    _description = "Construction BOQ Template"
    _order = "sequence, code"

    name = fields.Char("BOQ Item Name", required=True)
    code = fields.Char("BOQ Code", required=True)
    description = fields.Text("Description")
    sequence = fields.Integer("Sequence", default=10)

    template_id = fields.Many2one(
        "construction.project.template",
        string="Construction Template",
        required=True,
        ondelete="cascade",
    )
    task_template_id = fields.Many2one(
        "construction.task.template", string="Parent Task Template"
    )

    # Quantity and cost
    quantity = fields.Float("Quantity", default=1.0, required=True)
    unit_of_measure_id = fields.Many2one(
        "uom.uom", string="Unit of Measure", required=True
    )
    unit_cost = fields.Monetary(
        "Unit Cost", currency_field="currency_id", required=True
    )
    total_cost = fields.Monetary(
        "Total Cost", compute="_compute_total_cost", store=True
    )
    currency_id = fields.Many2one(
        "res.currency", related="template_id.company_id.currency_id"
    )

    # Cost classification
    cost_code_id = fields.Many2one(
        "construction.cost.code", string="Cost Code", required=True
    )

    # Product integration
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        help="Product associated with this BOQ item",
    )

    @api.depends("quantity", "unit_cost")
    def _compute_total_cost(self):
        for boq in self:
            boq.total_cost = boq.quantity * boq.unit_cost

    # SQL constraints
    _quantity_positive = models.Constraint(
        "CHECK(quantity > 0)",
        "Quantity must be positive!",
    )
    
    _unit_cost_positive = models.Constraint(
        "CHECK(unit_cost >= 0)",
        "Unit cost must be positive!",
    )
    
    _code_not_empty = models.Constraint(
        "CHECK(LENGTH(TRIM(code)) > 0)",
        "BOQ code cannot be empty!",
    )


class ConstructionCostEstimationTemplate(models.Model):
    """Cost estimation template for construction projects"""

    _name = "construction.cost.estimation.template"
    _description = "Construction Cost Estimation Template"
    _order = "sequence, name"

    name = fields.Char("Cost Item Name", required=True)
    description = fields.Text("Description")
    sequence = fields.Integer("Sequence", default=10)

    template_id = fields.Many2one(
        "construction.project.template",
        string="Construction Template",
        required=True,
        ondelete="cascade",
    )

    # Cost categories following Odoo 17 standards
    cost_category = fields.Selection(
        [
            ("material", "Construction Materials"),
            ("labour", "Construction Labour"),
            ("equipment", "Construction Equipment"),
            ("subcontractor", "Subcontractor Services"),
            ("miscellaneous", "Miscellaneous Costs"),
            ("overhead", "Overhead Costs"),
        ],
        string="Cost Category",
        required=True,
    )

    # Cost estimation
    estimated_cost = fields.Monetary(
        "Estimated Cost", currency_field="currency_id", required=True
    )
    contingency_percentage = fields.Float("Contingency %", default=10.0)
    total_cost = fields.Monetary(
        "Total Cost with Contingency", compute="_compute_total_cost", store=True
    )
    currency_id = fields.Many2one(
        "res.currency", related="template_id.company_id.currency_id"
    )

    # Historical data integration
    historical_average = fields.Monetary(
        "Historical Average", currency_field="currency_id", readonly=True
    )
    variance_percentage = fields.Float(
        "Variance from Historical", compute="_compute_variance_percentage"
    )

    @api.depends("estimated_cost", "contingency_percentage")
    def _compute_total_cost(self):
        for cost in self:
            contingency = cost.estimated_cost * (cost.contingency_percentage / 100)
            cost.total_cost = cost.estimated_cost + contingency

    @api.depends("estimated_cost", "historical_average")
    def _compute_variance_percentage(self):
        for cost in self:
            if cost.historical_average:
                cost.variance_percentage = (
                    (cost.estimated_cost - cost.historical_average)
                    / cost.historical_average
                ) * 100
            else:
                cost.variance_percentage = 0.0


class ConstructionResourceAllocationTemplate(models.Model):
    """Resource allocation template for construction tasks"""

    _name = "construction.resource.allocation.template"
    _description = "Construction Resource Allocation Template"
    _order = "sequence, name"

    name = fields.Char("Resource Name", required=True)
    description = fields.Text("Description")
    sequence = fields.Integer("Sequence", default=10)

    task_template_id = fields.Many2one(
        "construction.task.template",
        string="Task Template",
        required=True,
        ondelete="cascade",
    )
    template_id = fields.Many2one(
        "construction.project.template",
        related="task_template_id.template_id",
        store=True,
    )

    # Resource type
    resource_type = fields.Selection(
        [
            ("human", "Human Resource"),
            ("equipment", "Equipment"),
            ("material", "Material"),
            ("subcontractor", "Subcontractor"),
        ],
        string="Resource Type",
        required=True,
        help="Type of resource being allocated to the task",
    )

    # Resource details
    resource_id = fields.Many2one(
        "resource.resource",
        string="Resource",
        help="Specific resource from resource management",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product/Service",
        help="Product or service associated with this resource",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Supplier/Subcontractor",
        help="Supplier or subcontractor providing the resource",
    )

    # Allocation details
    allocated_quantity = fields.Float(
        "Allocated Quantity", default=1.0, help="Quantity of resource allocated"
    )
    unit_of_measure_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        help="Unit of measure for the allocated quantity",
    )
    duration_days = fields.Float(
        "Duration (Days)", default=1.0, help="Duration in days for resource allocation"
    )

    # Cost details
    unit_cost = fields.Monetary("Unit Cost", currency_field="currency_id")
    total_cost = fields.Monetary(
        "Total Cost", compute="_compute_total_cost", store=True
    )
    currency_id = fields.Many2one(
        "res.currency", related="template_id.company_id.currency_id"
    )

    @api.depends("allocated_quantity", "unit_cost")
    def _compute_total_cost(self):
        for allocation in self:
            allocation.total_cost = allocation.allocated_quantity * allocation.unit_cost


class ConstructionMilestoneTemplate(models.Model):
    """Milestone template for construction projects"""

    _name = "construction.milestone.template"
    _description = "Construction Milestone Template"
    _order = "sequence, name"

    name = fields.Char("Milestone Name", required=True)
    description = fields.Text("Description")
    sequence = fields.Integer("Sequence", default=10)

    task_template_id = fields.Many2one(
        "construction.task.template", string="Task Template", ondelete="cascade"
    )
    template_id = fields.Many2one(
        "construction.project.template", string="Project Template", ondelete="cascade"
    )

    # Milestone type
    milestone_type = fields.Selection(
        [
            ("start", "Project Start"),
            ("phase_completion", "Phase Completion"),
            ("delivery", "Delivery"),
            ("payment", "Payment Milestone"),
            ("approval", "Approval Required"),
            ("completion", "Project Completion"),
        ],
        string="Milestone Type",
        required=True,
        help="Type of milestone in the project lifecycle",
    )

    # Payment integration
    is_payment_milestone = fields.Boolean(
        "Is Payment Milestone",
        default=False,
        help="Check if this milestone triggers a payment",
    )
    payment_percentage = fields.Float(
        "Payment Percentage",
        help="Percentage of total project value to be paid at this milestone",
    )

    # Scheduling
    days_from_start = fields.Integer(
        "Days from Project Start",
        default=0,
        help="Number of days from project start when this milestone is due",
    )
    depends_on_task = fields.Boolean(
        "Depends on Task Completion",
        default=False,
        help="Check if this milestone depends on specific task completion",
    )

    # Deliverables
    deliverable_ids = fields.One2many(
        "construction.deliverable.template",
        "milestone_template_id",
        string="Deliverables",
    )


class ConstructionDeliverableTemplate(models.Model):
    """Deliverable template for construction milestones"""

    _name = "construction.deliverable.template"
    _description = "Construction Deliverable Template"
    _order = "sequence, name"

    name = fields.Char("Deliverable Name", required=True)
    description = fields.Text("Description")
    sequence = fields.Integer("Sequence", default=10)

    milestone_template_id = fields.Many2one(
        "construction.milestone.template",
        string="Milestone Template",
        required=True,
        ondelete="cascade",
    )

    # Deliverable type
    deliverable_type = fields.Selection(
        [
            ("document", "Document"),
            ("approval", "Approval"),
            ("inspection", "Inspection"),
            ("testing", "Testing"),
            ("delivery", "Physical Delivery"),
        ],
        string="Deliverable Type",
        required=True,
        help="Type of deliverable required for milestone completion",
    )

    # Requirements
    is_mandatory = fields.Boolean("Mandatory", default=True)
    approval_required = fields.Boolean("Approval Required", default=False)
    approver_ids = fields.Many2many(
        "res.users",
        "deliverable_approver_rel",
        "deliverable_id",
        "user_id",
        string="Approvers",
        help="Users who can approve this deliverable",
    )


class ConstructionTemplateVersion(models.Model):
    """Template version management for backup and versioning system"""

    _name = "construction.template.version"
    _description = "Construction Template Version"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "template_id, version desc"

    name = fields.Char("Version Name", compute="_compute_name", store=True)
    template_id = fields.Many2one(
        "construction.project.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )
    version = fields.Char("Version", required=True, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("archived", "Archived"),
        ],
        string="State",
        default="draft",
        tracking=True,
    )

    # Version metadata
    created_date = fields.Datetime("Created Date", default=fields.Datetime.now)
    created_by = fields.Many2one(
        "res.users", "Created By", default=lambda self: self.env.user
    )
    approved_date = fields.Datetime("Approved Date", readonly=True)
    approved_by = fields.Many2one("res.users", "Approved By", readonly=True)

    # Change tracking
    change_log = fields.Text("Change Log", tracking=True)
    previous_version_id = fields.Many2one(
        "construction.template.version", string="Previous Version"
    )

    # Backup data (JSON serialized template data)
    template_backup_data = fields.Text("Template Backup Data")

    # Performance analytics
    usage_count = fields.Integer("Usage Count", default=0)
    performance_score = fields.Float("Performance Score", default=0.0)
    avg_project_duration = fields.Float("Average Project Duration (Days)")
    avg_cost_variance = fields.Float("Average Cost Variance (%)")

    @api.depends("template_id", "version")
    def _compute_name(self):
        for record in self:
            record.name = f"{record.template_id.name} v{record.version}"

    def action_approve(self):
        """Approve template version"""
        self.ensure_one()
        self.write(
            {
                "state": "approved",
                "approved_date": fields.Datetime.now(),
                "approved_by": self.env.user.id,
            }
        )

        # Update main template version
        self.template_id.version = self.version
        self.template_id.state = "approved"

    def action_archive(self):
        """Archive template version"""
        self.ensure_one()
        self.state = "archived"

    def create_backup(self):
        """Create backup of current template data"""
        self.ensure_one()
        template_data = self._serialize_template_data()
        self.template_backup_data = json.dumps(template_data, indent=2)
        return True

    def _serialize_template_data(self):
        """Serialize template data for backup"""
        template = self.template_id
        return {
            "template": {
                "name": template.name,
                "description": template.description,
                "construction_category": template.construction_category,
                "version": template.version,
                "template_data": template.template_data,
            },
            "tasks": [
                {
                    "name": task.name,
                    "description": task.description,
                    "sequence": task.sequence,
                    "hierarchy_level": task.hierarchy_level,
                    "is_boq_item": task.is_boq_item,
                    "boq_code": task.boq_code,
                    "estimated_quantity": task.estimated_quantity,
                    "unit_cost": task.unit_cost,
                    "parent_template_id": (
                        task.parent_template_id.id if task.parent_template_id else None
                    ),
                }
                for task in template.task_template_ids
            ],
            "boq_items": [
                {
                    "name": boq.name,
                    "code": boq.code,
                    "description": boq.description,
                    "quantity": boq.quantity,
                    "unit_cost": boq.unit_cost,
                    "sequence": boq.sequence,
                }
                for boq in template.boq_template_ids
            ],
            "milestones": [
                {
                    "name": milestone.name,
                    "description": milestone.description,
                    "milestone_type": milestone.milestone_type,
                    "days_from_start": milestone.days_from_start,
                    "is_payment_milestone": milestone.is_payment_milestone,
                    "payment_percentage": milestone.payment_percentage,
                }
                for milestone in template.milestone_template_ids
            ],
            "cost_estimations": [
                {
                    "name": cost.name,
                    "description": cost.description,
                    "cost_category": cost.cost_category,
                    "estimated_cost": cost.estimated_cost,
                    "contingency_percentage": cost.contingency_percentage,
                }
                for cost in template.cost_estimation_ids
            ],
        }


class ConstructionTemplateImportExport(models.TransientModel):
    """Template import/export functionality for sharing between systems"""

    _name = "construction.template.import.export"
    _description = "Construction Template Import/Export"

    operation = fields.Selection(
        [("import", "Import"), ("export", "Export")],
        string="Operation",
        required=True,
        default="export",
    )

    # Export fields
    template_ids = fields.Many2many(
        "construction.project.template",
        "template_export_rel",
        "export_id",
        "template_id",
        string="Templates to Export",
    )
    include_versions = fields.Boolean("Include Version History", default=True)
    include_analytics = fields.Boolean("Include Performance Analytics", default=False)

    # Import fields
    import_file = fields.Binary("Import File", help="ZIP file containing template data")
    import_filename = fields.Char("Filename")
    overwrite_existing = fields.Boolean("Overwrite Existing Templates", default=False)
    create_backup = fields.Boolean("Create Backup Before Import", default=True)

    # Export result
    export_file = fields.Binary("Export File", readonly=True)
    export_filename = fields.Char("Export Filename", readonly=True)

    # Import/Export log
    operation_log = fields.Text("Operation Log", readonly=True)

    def action_export_templates(self):
        """Export selected templates to ZIP file"""
        self.ensure_one()
        if not self.template_ids:
            raise UserError(_("Please select at least one template to export."))

        export_data = {}
        log_messages = []

        try:
            for template in self.template_ids:
                template_data = self._export_template_data(template)
                export_data[f"template_{template.id}"] = template_data
                log_messages.append(f"Exported template: {template.name}")

            # Create ZIP file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # Add main template data
                zip_file.writestr(
                    "templates.json", json.dumps(export_data, indent=2, default=str)
                )

                # Add metadata
                metadata = {
                    "export_date": fields.Datetime.now().isoformat(),
                    "export_user": self.env.user.name,
                    "odoo_version": "17.0",
                    "module_version": "1.0",
                    "template_count": len(self.template_ids),
                }
                zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))

            zip_buffer.seek(0)
            export_filename = (
                f"construction_templates_{fields.Date.today().strftime('%Y%m%d')}.zip"
            )

            self.write(
                {
                    "export_file": base64.b64encode(zip_buffer.getvalue()),
                    "export_filename": export_filename,
                    "operation_log": "\n".join(log_messages),
                }
            )

            log_messages.append(f"Export completed successfully: {export_filename}")

        except Exception as e:
            log_messages.append(f"Export failed: {str(e)}")
            raise UserError(_("Export failed: %s") % str(e))

        self.operation_log = "\n".join(log_messages)

        return {
            "type": "ir.actions.act_window",
            "res_model": "construction.template.import.export",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_import_templates(self):
        """Import templates from ZIP file"""
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Please select a file to import."))

        log_messages = []
        imported_count = 0

        try:
            # Decode and extract ZIP file
            zip_data = base64.b64decode(self.import_file)
            zip_buffer = io.BytesIO(zip_data)

            with zipfile.ZipFile(zip_buffer, "r") as zip_file:
                # Read metadata
                if "metadata.json" in zip_file.namelist():
                    metadata = json.loads(
                        zip_file.read("metadata.json").decode("utf-8")
                    )
                    log_messages.append(f"Import metadata: {metadata}")

                # Read template data
                if "templates.json" not in zip_file.namelist():
                    raise UserError(_("Invalid template file: missing templates.json"))

                templates_data = json.loads(
                    zip_file.read("templates.json").decode("utf-8")
                )

                # Import each template
                for template_key, template_data in templates_data.items():
                    try:
                        self._import_template_data(template_data)
                        imported_count += 1
                        log_messages.append(
                            f"Imported template: {template_data['template']['name']}"
                        )
                    except Exception as e:
                        log_messages.append(
                            f"Failed to import {template_key}: {str(e)}"
                        )

            log_messages.append(
                f"Import completed: {imported_count} templates imported"
            )

        except Exception as e:
            log_messages.append(f"Import failed: {str(e)}")
            raise UserError(_("Import failed: %s") % str(e))

        self.operation_log = "\n".join(log_messages)

        return {
            "type": "ir.actions.act_window",
            "res_model": "construction.template.import.export",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _export_template_data(self, template):
        """Export single template data"""
        version_obj = self.env["construction.template.version"]
        latest_version = version_obj.search(
            [("template_id", "=", template.id)], order="version desc", limit=1
        )

        if latest_version and latest_version.template_backup_data:
            return json.loads(latest_version.template_backup_data)
        else:
            # Create backup data on the fly
            return latest_version._serialize_template_data() if latest_version else {}

    def _import_template_data(self, template_data):
        """Import single template data"""
        template_info = template_data.get("template", {})

        # Check if template exists
        existing_template = self.env["construction.project.template"].search(
            [
                ("name", "=", template_info.get("name")),
                (
                    "construction_category",
                    "=",
                    template_info.get("construction_category"),
                ),
            ],
            limit=1,
        )

        if existing_template and not self.overwrite_existing:
            raise UserError(
                _(
                    "Template '%s' already exists. Enable 'Overwrite Existing' to replace it."
                )
                % template_info.get("name")
            )

        # Create backup if requested
        if existing_template and self.create_backup:
            self._create_template_backup(existing_template)

        # Create or update template
        template_vals = {
            "name": template_info.get("name"),
            "description": template_info.get("description"),
            "construction_category": template_info.get("construction_category"),
            "version": template_info.get("version", "1.0"),
            "template_data": template_info.get("template_data"),
            "state": "draft",  # Always import as draft for review
        }

        if existing_template:
            template = existing_template
            template.write(template_vals)
        else:
            template = self.env["construction.project.template"].create(template_vals)

        # Import related data
        self._import_task_templates(template, template_data.get("tasks", []))
        self._import_boq_templates(template, template_data.get("boq_items", []))
        self._import_milestone_templates(template, template_data.get("milestones", []))
        self._import_cost_estimation_templates(
            template, template_data.get("cost_estimations", [])
        )

        return template

    def _create_template_backup(self, template):
        """Create backup before import"""
        version_obj = self.env["construction.template.version"]
        backup_version = version_obj.create(
            {
                "template_id": template.id,
                "version": f"{template.version}_backup_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "state": "archived",
                "change_log": f"Backup created before import on {fields.Datetime.now()}",
            }
        )
        backup_version.create_backup()

    def _import_task_templates(self, template, tasks_data):
        """Import task templates"""
        # Clear existing tasks if overwriting
        if self.overwrite_existing:
            template.task_template_ids.unlink()

        task_mapping = {}  # To handle parent-child relationships

        for task_data in tasks_data:
            task_vals = {
                "template_id": template.id,
                "name": task_data.get("name"),
                "description": task_data.get("description"),
                "sequence": task_data.get("sequence", 10),
                "hierarchy_level": task_data.get("hierarchy_level", "work_package"),
                "is_boq_item": task_data.get("is_boq_item", False),
                "boq_code": task_data.get("boq_code"),
                "estimated_quantity": task_data.get("estimated_quantity", 1.0),
                "unit_cost": task_data.get("unit_cost", 0.0),
            }

            task = self.env["construction.task.template"].create(task_vals)
            task_mapping[task_data.get("id")] = task

        # Set parent relationships in second pass
        for task_data in tasks_data:
            if task_data.get("parent_template_id"):
                parent_task = task_mapping.get(task_data["parent_template_id"])
                if parent_task:
                    task_mapping[task_data.get("id")].parent_template_id = (
                        parent_task.id
                    )

    def _import_boq_templates(self, template, boq_data):
        """Import BOQ templates"""
        if self.overwrite_existing:
            template.boq_template_ids.unlink()

        for boq_item in boq_data:
            self.env["construction.boq.template"].create(
                {
                    "template_id": template.id,
                    "name": boq_item.get("name"),
                    "code": boq_item.get("code"),
                    "description": boq_item.get("description"),
                    "quantity": boq_item.get("quantity", 1.0),
                    "unit_cost": boq_item.get("unit_cost", 0.0),
                    "sequence": boq_item.get("sequence", 10),
                    "unit_of_measure_id": self.env.ref(
                        "uom.product_uom_unit"
                    ).id,  # Default UOM
                }
            )

    def _import_milestone_templates(self, template, milestone_data):
        """Import milestone templates"""
        if self.overwrite_existing:
            template.milestone_template_ids.unlink()

        for milestone in milestone_data:
            self.env["construction.milestone.template"].create(
                {
                    "template_id": template.id,
                    "name": milestone.get("name"),
                    "description": milestone.get("description"),
                    "milestone_type": milestone.get(
                        "milestone_type", "phase_completion"
                    ),
                    "days_from_start": milestone.get("days_from_start", 0),
                    "is_payment_milestone": milestone.get(
                        "is_payment_milestone", False
                    ),
                    "payment_percentage": milestone.get("payment_percentage", 0.0),
                }
            )

    def _import_cost_estimation_templates(self, template, cost_data):
        """Import cost estimation templates"""
        if self.overwrite_existing:
            template.cost_estimation_ids.unlink()

        for cost_item in cost_data:
            self.env["construction.cost.estimation.template"].create(
                {
                    "template_id": template.id,
                    "name": cost_item.get("name"),
                    "description": cost_item.get("description"),
                    "cost_category": cost_item.get("cost_category", "material"),
                    "estimated_cost": cost_item.get("estimated_cost", 0.0),
                    "contingency_percentage": cost_item.get(
                        "contingency_percentage", 10.0
                    ),
                }
            )


class ConstructionTemplateAnalytics(models.Model):
    """Template performance analytics and usage tracking"""

    _name = "construction.template.analytics"
    _description = "Construction Template Analytics"
    _rec_name = "template_id"
    _order = "template_id, period_start desc"

    template_id = fields.Many2one(
        "construction.project.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )

    # Analytics period
    period_start = fields.Date("Period Start", required=True)
    period_end = fields.Date("Period End", required=True)

    # Usage metrics
    projects_created = fields.Integer("Projects Created", default=0)
    projects_completed = fields.Integer("Projects Completed", default=0)
    projects_cancelled = fields.Integer("Projects Cancelled", default=0)
    success_rate = fields.Float(
        "Success Rate (%)", compute="_compute_success_rate", store=True
    )

    # Performance metrics
    avg_duration_planned = fields.Float("Average Planned Duration (Days)")
    avg_duration_actual = fields.Float("Average Actual Duration (Days)")
    duration_variance = fields.Float(
        "Duration Variance (%)", compute="_compute_duration_variance", store=True
    )

    avg_cost_planned = fields.Monetary(
        "Average Planned Cost", currency_field="currency_id"
    )
    avg_cost_actual = fields.Monetary(
        "Average Actual Cost", currency_field="currency_id"
    )
    cost_variance = fields.Float(
        "Cost Variance (%)", compute="_compute_cost_variance", store=True
    )
    currency_id = fields.Many2one(
        "res.currency", related="template_id.company_id.currency_id"
    )

    # Quality metrics
    avg_quality_score = fields.Float("Average Quality Score")
    customer_satisfaction = fields.Float("Customer Satisfaction Score")
    defect_rate = fields.Float("Defect Rate (%)")

    # Resource utilization
    resource_efficiency = fields.Float("Resource Efficiency (%)")
    material_waste_percentage = fields.Float("Material Waste (%)")

    # Recommendations
    performance_score = fields.Float(
        "Overall Performance Score", compute="_compute_performance_score", store=True
    )
    recommendations = fields.Text("Recommendations")
    improvement_areas = fields.Text("Areas for Improvement")

    @api.depends("projects_created", "projects_completed", "projects_cancelled")
    def _compute_success_rate(self):
        for record in self:
            total_finished = record.projects_completed + record.projects_cancelled
            if total_finished > 0:
                record.success_rate = (record.projects_completed / total_finished) * 100
            else:
                record.success_rate = 0.0

    @api.depends("avg_duration_planned", "avg_duration_actual")
    def _compute_duration_variance(self):
        for record in self:
            if record.avg_duration_planned > 0:
                record.duration_variance = (
                    (record.avg_duration_actual - record.avg_duration_planned)
                    / record.avg_duration_planned
                ) * 100
            else:
                record.duration_variance = 0.0

    @api.depends("avg_cost_planned", "avg_cost_actual")
    def _compute_cost_variance(self):
        for record in self:
            if record.avg_cost_planned > 0:
                record.cost_variance = (
                    (record.avg_cost_actual - record.avg_cost_planned)
                    / record.avg_cost_planned
                ) * 100
            else:
                record.cost_variance = 0.0

    @api.depends(
        "success_rate",
        "duration_variance",
        "cost_variance",
        "avg_quality_score",
        "resource_efficiency",
    )
    def _compute_performance_score(self):
        for record in self:
            # Weighted performance score calculation
            score = 0.0

            # Success rate (30% weight)
            score += (record.success_rate / 100) * 30

            # Duration performance (20% weight) - lower variance is better
            duration_score = max(0, 100 - abs(record.duration_variance)) / 100
            score += duration_score * 20

            # Cost performance (25% weight) - lower variance is better
            cost_score = max(0, 100 - abs(record.cost_variance)) / 100
            score += cost_score * 25

            # Quality score (15% weight)
            score += (
                record.avg_quality_score / 10
            ) * 15  # Assuming quality score is out of 10

            # Resource efficiency (10% weight)
            score += (record.resource_efficiency / 100) * 10

            record.performance_score = min(100, score)

            _logger.error(f"Failed to run monthly analytics generation: {str(e)}")

    @api.model
    def generate_analytics(self, template_id, period_start, period_end):
        """Generate analytics for a template in a given period"""
        template = self.env["construction.project.template"].browse(template_id)
        if not template.exists():
            return False

        # Get projects created from this template in the period
        projects = self.env["project.project"].search(
            [
                ("construction_template_id", "=", template_id),
                ("create_date", ">=", period_start),
                ("create_date", "<=", period_end),
            ]
        )

        if not projects:
            return False

        # Calculate metrics
        analytics_data = self._calculate_template_metrics(
            projects, period_start, period_end
        )
        analytics_data["template_id"] = template_id

        # Create or update analytics record
        existing_analytics = self.search(
            [
                ("template_id", "=", template_id),
                ("period_start", "=", period_start),
                ("period_end", "=", period_end),
            ],
            limit=1,
        )

        if existing_analytics:
            existing_analytics.write(analytics_data)
            return existing_analytics
        else:
            return self.create(analytics_data)

    def _calculate_template_metrics(self, projects, period_start, period_end):
        """Calculate performance metrics for projects"""
        total_projects = len(projects)
        completed_projects = projects.filtered(lambda p: p.stage_id.name == "Completed")
        cancelled_projects = projects.filtered(lambda p: p.stage_id.name == "Cancelled")

        # Duration metrics
        planned_durations = []
        actual_durations = []

        for project in completed_projects:
            if project.date_start and project.date:
                planned_duration = (project.date - project.date_start).days
                planned_durations.append(planned_duration)

                # Calculate actual duration if project is completed
                if hasattr(project, "actual_end_date") and project.actual_end_date:
                    actual_duration = (
                        project.actual_end_date - project.date_start
                    ).days
                    actual_durations.append(actual_duration)

        # Cost metrics
        planned_costs = projects.mapped("contract_value")
        actual_costs = []

        for project in projects:
            # Calculate actual costs from analytic lines
            analytic_lines = self.env["account.analytic.line"].search(
                [
                    ("project_id", "=", project.id),
                    ("amount", "<", 0),  # Costs are negative
                ]
            )
            actual_cost = sum(abs(line.amount) for line in analytic_lines)
            if actual_cost > 0:
                actual_costs.append(actual_cost)

        return {
            "period_start": period_start,
            "period_end": period_end,
            "projects_created": total_projects,
            "projects_completed": len(completed_projects),
            "projects_cancelled": len(cancelled_projects),
            "avg_duration_planned": (
                sum(planned_durations) / len(planned_durations)
                if planned_durations
                else 0
            ),
            "avg_duration_actual": (
                sum(actual_durations) / len(actual_durations) if actual_durations else 0
            ),
            "avg_cost_planned": (
                sum(planned_costs) / len(planned_costs) if planned_costs else 0
            ),
            "avg_cost_actual": (
                sum(actual_costs) / len(actual_costs) if actual_costs else 0
            ),
            "avg_quality_score": 8.0,  # Default quality score - would be calculated from quality records
            "customer_satisfaction": 85.0,  # Default satisfaction - would be from surveys
            "resource_efficiency": 80.0,  # Default efficiency - would be calculated from resource utilization
        }

    @api.model
    def generate_recommendations(self, template_id):
        """Generate recommendations based on analytics"""
        latest_analytics = self.search(
            [("template_id", "=", template_id)], order="period_end desc", limit=1
        )

        if not latest_analytics:
            return "No analytics data available for recommendations."

        recommendations = []

        # Success rate recommendations
        if latest_analytics.success_rate < 70:
            recommendations.append(
                "Low success rate detected. Review project scope definition and resource allocation."
            )

        # Duration variance recommendations
        if abs(latest_analytics.duration_variance) > 20:
            if latest_analytics.duration_variance > 0:
                recommendations.append(
                    "Projects consistently exceed planned duration. Consider more realistic time estimates or additional resources."
                )
            else:
                recommendations.append(
                    "Projects complete faster than planned. Consider optimizing resource allocation or taking on more projects."
                )

        # Cost variance recommendations
        if abs(latest_analytics.cost_variance) > 15:
            if latest_analytics.cost_variance > 0:
                recommendations.append(
                    "Cost overruns detected. Review cost estimation accuracy and implement better cost controls."
                )
            else:
                recommendations.append(
                    "Projects under budget. Consider more competitive pricing or reinvesting savings in quality improvements."
                )

        # Quality recommendations
        if latest_analytics.avg_quality_score < 7:
            recommendations.append(
                "Quality scores below target. Implement additional quality checkpoints and training."
            )

        # Resource efficiency recommendations
        if latest_analytics.resource_efficiency < 75:
            recommendations.append(
                "Low resource efficiency. Review resource allocation and consider workflow optimization."
            )

        return (
            "\n".join(recommendations)
            if recommendations
            else "Template performance is within acceptable ranges."
        )

    @api.model
    def _cron_generate_monthly_analytics(self):
        """Cron job to generate monthly analytics for all templates"""
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta

        # Calculate previous month period
        today = datetime.now().date()
        period_end = today.replace(day=1) - timedelta(
            days=1
        )  # Last day of previous month
        period_start = period_end.replace(day=1)  # First day of previous month

        # Get all active templates
        templates = self.env["construction.project.template"].search(
            [("active", "=", True)]
        )
        analytics_count = 0

        for template in templates:
            try:
                analytics = self.generate_analytics(
                    template.id, period_start, period_end
                )
                if analytics:
                    analytics_count += 1
            except Exception as e:
                _logger.error(
                    f"Failed to generate analytics for template {template.name}: {str(e)}"
                )

        _logger.info(
            f"Generated analytics for {analytics_count} templates for period {period_start} to {period_end}"
        )
        return analytics_count


class ConstructionTemplateUsageLog(models.Model):
    """Log template usage for detailed tracking"""

    _name = "construction.template.usage.log"
    _description = "Construction Template Usage Log"
    _order = "usage_date desc"

    template_id = fields.Many2one(
        "construction.project.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
    )

    # Usage details
    usage_date = fields.Datetime("Usage Date", default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", "User", default=lambda self: self.env.user)
    usage_type = fields.Selection(
        [
            ("create", "Project Creation"),
            ("copy", "Template Copy"),
            ("modify", "Template Modification"),
            ("export", "Template Export"),
        ],
        string="Usage Type",
        required=True,
    )

    # Context information
    sale_order_id = fields.Many2one("sale.order", "Related Sale Order")
    customizations_applied = fields.Text("Customizations Applied")
    notes = fields.Text("Notes")

    # Performance tracking
    creation_duration = fields.Float("Creation Duration (seconds)")
    success = fields.Boolean("Success", default=True)
    error_message = fields.Text("Error Message")

    @api.model
    def log_template_usage(self, template_id, project_id, usage_type, **kwargs):
        """Log template usage"""
        return self.create(
            {
                "template_id": template_id,
                "project_id": project_id,
                "usage_type": usage_type,
                "sale_order_id": kwargs.get("sale_order_id"),
                "customizations_applied": kwargs.get("customizations_applied"),
                "notes": kwargs.get("notes"),
                "creation_duration": kwargs.get("creation_duration", 0),
                "success": kwargs.get("success", True),
                "error_message": kwargs.get("error_message"),
            }
        )


class ProductTemplate(models.Model):
    """Extend product template to integrate with construction templates"""

    _inherit = "product.template"

    construction_template_id = fields.Many2one(
        "construction.project.template",
        string="Construction Template",
        help="Construction template to use when this service product creates a project",
    )

    @api.onchange("service_tracking")
    def _onchange_service_tracking_construction(self):
        """Clear construction template if not creating projects"""
        if self.service_tracking not in ["task_in_project", "project_only"]:
            self.construction_template_id = False


class SaleOrder(models.Model):
    """Extend sale order to integrate with construction templates"""

    _inherit = "sale.order"

    def action_confirm(self):
        """Override to apply construction templates when projects are created"""
        result = super().action_confirm()

        # Apply construction templates to created projects
        for order in self:
            order._apply_construction_templates_to_projects()

        return result

    def _apply_construction_templates_to_projects(self):
        """Apply construction templates to projects created from this sale order"""
        self.ensure_one()

        # Find projects created from this sale order
        projects = self.env["project.project"].search([("sale_order_id", "=", self.id)])

        # Also check for projects linked via sale order lines
        if not projects:
            projects = self.env["project.project"].search(
                [("sale_line_id", "in", self.order_line.ids)]
            )

        for project in projects:
            # Find construction template from sale order lines
            construction_template = self._get_construction_template_for_project(project)

            if construction_template:
                # Update project with construction template
                project.write(
                    {
                        "is_construction": True,
                        "construction_template_id": construction_template.id,
                    }
                )

                # Apply construction template structure
                construction_template._apply_construction_template(project)

                _logger.info(
                    "Applied construction template '%s' to project '%s' from sale order '%s'",
                    construction_template.name,
                    project.name,
                    self.name,
                )

    def _get_construction_template_for_project(self, project):
        """Get the appropriate construction template for a project"""
        self.ensure_one()

        # Priority 1: Check if project was created from a specific sale line with construction template
        if (
            project.sale_line_id
            and project.sale_line_id.product_id.construction_template_id
        ):
            return project.sale_line_id.product_id.construction_template_id

        # Priority 2: Find construction products in sale order lines
        construction_lines = self.order_line.filtered(
            lambda line: line.product_id.construction_template_id
        )

        if construction_lines:
            # Use the first construction template found
            return construction_lines[0].product_id.construction_template_id

        # Priority 3: Check for service products that create projects with construction templates
        service_lines = self.order_line.filtered(
            lambda line: line.product_id.service_tracking
            in ["task_in_project", "project_only"]
            and line.product_id.construction_template_id
        )

        if service_lines:
            return service_lines[0].product_id.construction_template_id

        return False


class SaleOrderLine(models.Model):
    """Extend sale order line to integrate with construction templates"""

    _inherit = "sale.order.line"

    def _timesheet_create_project(self):
        """Override to use construction template if available"""
        project = super()._timesheet_create_project()

        # Apply construction template if product has one
        if self.product_id.construction_template_id:
            construction_template = self.product_id.construction_template_id

            # Update project with construction template
            project.write(
                {
                    "is_construction": True,
                    "construction_template_id": construction_template.id,
                }
            )

            # Apply construction-specific features
            construction_template._apply_construction_template(project)

        return project

    def _timesheet_create_project_prepare_values(self):
        """Override to include construction-specific values"""
        values = super()._timesheet_create_project_prepare_values()

        # Add construction template if available
        if self.product_id.construction_template_id:
            values.update(
                {
                    "is_construction": True,
                    "construction_template_id": self.product_id.construction_template_id.id,
                }
            )

        return values


class ProjectTask(models.Model):
    """Extend project task for construction BOQ integration"""

    _inherit = "project.task"

    # BOQ identification
    is_boq_item = fields.Boolean("Is BOQ Item", default=False)
    boq_code = fields.Char("BOQ Code", index=True)

    # Milestone identification
    is_milestone = fields.Boolean("Is Milestone", default=False)

    # Quantity and cost tracking
    estimated_quantity = fields.Float("Estimated Quantity", default=1.0)
    revised_quantity = fields.Float("Revised Quantity")
    actual_quantity = fields.Float("Actual Quantity")
    unit_of_measure_id = fields.Many2one("uom.uom", "Unit of Measure")

    # Cost calculations
    unit_cost = fields.Monetary("Unit Cost", currency_field="currency_id")
    boq_value = fields.Monetary("BOQ Value", compute="_compute_boq_value", store=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")

    # Cost code integration
    cost_code_id = fields.Many2one("construction.cost.code", "Cost Code")

    # Product integration for BOQ items
    product_id = fields.Many2one("product.product", "Product")

    @api.depends("revised_quantity", "estimated_quantity", "unit_cost")
    def _compute_boq_value(self):
        for task in self:
            quantity = task.revised_quantity or task.estimated_quantity
            task.boq_value = quantity * task.unit_cost

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """Update task fields when product is selected"""
        if self.product_id:
            self.name = self.product_id.name
            self.unit_cost = (
                self.product_id.construction_unit_cost or self.product_id.standard_price
            )
            self.unit_of_measure_id = self.product_id.uom_id

            if self.product_id.construction_cost_code_id:
                self.cost_code_id = self.product_id.construction_cost_code_id

            if self.product_id.is_boq_item:
                self.is_boq_item = True
