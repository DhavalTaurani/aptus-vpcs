# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class ConstructionTemplateCustomizationWizard(models.TransientModel):
    """Wizard for customizing construction project templates"""
    _name = 'construction.template.customization.wizard'
    _description = 'Construction Template Customization Wizard'

    # Template selection
    template_id = fields.Many2one(
        'construction.project.template',
        string='Base Template',
        required=True,
        domain=[('state', '=', 'approved')],
        help="Select an approved construction template as the base for your project"
    )
    
    # Project details
    project_name = fields.Char('Project Name', required=True,
                                help="Name of the construction project to be created")
    project_description = fields.Text('Project Description',
                                    help="Detailed description of the construction project")
    
    # Customization options
    customize_tasks = fields.Boolean('Customize Tasks', default=True,
                                    help="Enable customization of task templates (includes BOQ items)")
    customize_boq = fields.Boolean('Customize BOQ Items', default=False, readonly=True,
                                    help="BOQ items are now managed through task templates only")
    customize_milestones = fields.Boolean('Customize Milestones', default=False, readonly=True,
                                        help="Milestones are now dynamic based on payment terms")
    customize_resources = fields.Boolean('Customize Resources', default=False,
                                        help="Enable customization of resource allocation templates")
    
    # Conflict resolution options
    conflict_resolution = fields.Selection([
        ('auto_rename', 'Auto-rename conflicting BOQ codes'),
        ('skip_existing', 'Skip items with existing BOQ codes'),
        ('replace_existing', 'Replace existing items with template items'),
    ], string='BOQ Code Conflict Resolution', default='auto_rename',
        help="How to handle BOQ codes that already exist in the project")
    
    # Task customization
    task_customization_ids = fields.One2many(
        'construction.template.task.customization',
        'wizard_id',
        string='Task Customizations'
    )
    
    # BOQ customization
    boq_customization_ids = fields.One2many(
        'construction.template.boq.customization',
        'wizard_id',
        string='BOQ Customizations'
    )
    
    # Milestone customization
    milestone_customization_ids = fields.One2many(
        'construction.template.milestone.customization',
        'wizard_id',
        string='Milestone Customizations'
    )
    
    # Project settings
    contract_value = fields.Monetary('Contract Value', currency_field='currency_id',
                                    help="Total contract value for the construction project")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id,
                                help="Currency for the project contract")
    start_date = fields.Date('Project Start Date', default=fields.Date.today,
                            help="Planned start date for the construction project")
    end_date = fields.Date('Project End Date',
                            help="Planned end date for the construction project")
    
    # Customer information
    partner_id = fields.Many2one('res.partner', string='Customer',
                                help="Customer or client for the construction project")
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Load template data for customization"""
        if not self.template_id:
            return
            
        # Clear existing customizations
        self.task_customization_ids = [(5, 0, 0)]
        self.boq_customization_ids = [(5, 0, 0)]
        self.milestone_customization_ids = [(5, 0, 0)]
        
        # Load task templates (which include BOQ items)
        if self.customize_tasks:
            task_lines = []
            for task_template in self.template_id.task_template_ids:
                task_lines.append((0, 0, {
                    'task_template_id': task_template.id,
                    'name': task_template.name,
                    'description': task_template.description,
                    'estimated_quantity': task_template.estimated_quantity,
                    'unit_cost': task_template.unit_cost,
                    'include_in_project': True,
                }))
            self.task_customization_ids = task_lines
        
        # Note: BOQ items are now handled through task templates only
        # Milestones are now dynamic based on payment terms, so no customization needed
    
    def action_create_project(self):
        """Create customized construction project"""
        self.ensure_one()
        
        if not self.template_id:
            raise ValidationError(_("Please select a base template."))
        
        # Create project with basic information
        project_vals = {
            'name': self.project_name,
            'description': self.project_description,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'is_construction': True,
            'construction_template_id': self.template_id.id,
            'contract_value': self.contract_value,
            'contract_start_date': self.start_date,
            'contract_end_date': self.end_date,
        }
        
        # Create project using customized template application
        project = self._create_customized_project(project_vals)
        
        # Return action to view the created project
        return {
            'type': 'ir.actions.act_window',
            'name': _('Construction Project'),
            'res_model': 'project.project',
            'res_id': project.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _create_customized_project(self, project_vals):
        """Create project with customized template application"""
        self.ensure_one()
        
        # Create base project without applying template yet
        if self.template_id.project_template_id:
            # Use standard Odoo copy mechanism for base project
            project = self.template_id.project_template_id.copy(project_vals)
            # Update with construction-specific fields
            project.write({
                'is_construction': True,
                'construction_template_id': self.template_id.id,
            })
        else:
            # Create new project directly
            project = self.env["project.project"].create(project_vals)
        
        # Apply customized template features
        self._apply_customized_template(project)
        
        return project
    
    def _apply_customized_template(self, project):
        """Apply template with customizations instead of standard template application"""
        self.ensure_one()
        
        # Apply customized tasks (which include BOQ items) - NO SEPARATE BOQ CREATION
        if self.customize_tasks:
            self._create_customized_tasks(project)
        else:
            # Apply standard task templates with conflict resolution
            self.template_id._apply_template_tasks(project, self.conflict_resolution)
        
        # Apply dynamic milestones based on payment terms (not customizable in wizard)
        # This will use progressive payment terms if available, otherwise template milestones
        self.template_id._apply_dynamic_milestones(project)
        
        # Apply cost estimations (not customizable in wizard)
        self.template_id._apply_template_cost_estimations(project)
    
    def _create_customized_tasks(self, project):
        """Create customized tasks from wizard selections"""
        task_mapping = {}
        
        # OPTIMIZATION: Get all existing BOQ codes in one query
        existing_boq_codes = set()
        if self.conflict_resolution in ["auto_rename", "skip_existing"]:
            existing_tasks = self.env["project.task"].search([
                ("project_id", "=", project.id),
                ("is_boq_item", "=", True),
                ("boq_code", "!=", False)
            ])
            existing_boq_codes = set(existing_tasks.mapped('boq_code'))

        # Create single BOQ code map to track conflicts and resolutions
        boq_code_map = {}  # Map original_code -> resolved_code
        
        # Get included task customizations sorted by hierarchy
        included_tasks = self.task_customization_ids.filtered('include_in_project')
        
        # Sort by template hierarchy and sequence
        hierarchy_order = ['project', 'phase', 'work_package']
        sorted_customizations = included_tasks.sorted(
            key=lambda c: (
                hierarchy_order.index(c.task_template_id.hierarchy_level),
                c.task_template_id.sequence,
                c.task_template_id.id
            )
        )
        
        for customization in sorted_customizations:
            task_template = customization.task_template_id
            
            # Handle BOQ code conflicts using optimized approach
            boq_code = task_template.boq_code
            if task_template.is_boq_item and boq_code:
                boq_code = self._resolve_boq_code_conflict_optimized(
                    boq_code, existing_boq_codes, boq_code_map, project.name
                )
                
                # Skip this task if conflict resolution returned None
                if boq_code is None:
                    continue
            
            # Prepare customized task values
            task_vals = {
                'name': customization.name,
                'description': customization.description,
                'project_id': project.id,
                'sequence': task_template.sequence,
                'is_boq_item': task_template.is_boq_item,
                'boq_code': boq_code,
                'estimated_quantity': customization.estimated_quantity,
                'unit_cost': customization.unit_cost,
                'unit_of_measure_id': task_template.unit_of_measure_id.id if task_template.unit_of_measure_id else False,
                'cost_code_id': task_template.cost_code_id.id if task_template.cost_code_id else False,
            }
            
            # Set parent task if exists
            if task_template.parent_template_id and task_template.parent_template_id.id in task_mapping:
                task_vals['parent_id'] = task_mapping[task_template.parent_template_id.id]
            
            # Create task
            task = self.env['project.task'].create(task_vals)
            task_mapping[task_template.id] = task.id
    
    # Note: BOQ items and milestones are no longer customized separately
    # BOQ items are handled through task templates
    # Milestones are dynamic based on payment terms from progressive payment module
    
    def _resolve_boq_code_conflict_optimized(
        self, original_code, existing_boq_codes, boq_code_map, project_name
    ):
        """Optimized BOQ code conflict resolution using single query and in-memory processing"""
        if not original_code:
            return original_code

        # Check if we already resolved this code
        if original_code in boq_code_map:
            return boq_code_map[original_code]

        # Check if the code conflicts with existing codes
        if original_code not in existing_boq_codes:
            # No conflict, add to map and existing codes set
            boq_code_map[original_code] = original_code
            existing_boq_codes.add(original_code)
            return original_code

        # Handle conflict based on strategy
        if self.conflict_resolution == "skip_existing":
            _logger.info(
                "Skipping BOQ item with code '%s' - already exists in project '%s'",
                original_code,
                project_name,
            )
            boq_code_map[original_code] = None
            return None

        elif self.conflict_resolution == "replace_existing":
            # For replace_existing, we would need to handle task deletion separately
            # For now, log and use original code (task deletion handled elsewhere)
            _logger.info(
                "Replacing existing BOQ item with code '%s' in project '%s'",
                original_code,
                project_name,
            )
            boq_code_map[original_code] = original_code
            return original_code

        else:  # auto_rename (default)
            # Generate unique code using in-memory check (no database queries)
            counter = 1
            new_code = f"{original_code}-{counter:03d}"

            # Check against both existing codes and already resolved codes
            while (new_code in existing_boq_codes or 
                    new_code in boq_code_map.values()):
                counter += 1
                new_code = f"{original_code}-{counter:03d}"

            # Add to maps
            boq_code_map[original_code] = new_code
            existing_boq_codes.add(new_code)

            _logger.warning(
                "BOQ code conflict resolved: '%s' changed to '%s' in project '%s'",
                original_code,
                new_code,
                project_name,
            )

            return new_code



class ConstructionTemplateTaskCustomization(models.TransientModel):
    """Task customization line"""
    _name = 'construction.template.task.customization'
    _description = 'Construction Template Task Customization'

    wizard_id = fields.Many2one('construction.template.customization.wizard', required=True, ondelete='cascade')
    task_template_id = fields.Many2one('construction.task.template', required=True)
    
    # Customizable fields
    name = fields.Char('Task Name', required=True)
    description = fields.Text('Description')
    estimated_quantity = fields.Float('Estimated Quantity', default=1.0)
    unit_cost = fields.Monetary('Unit Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')
    
    # Control fields
    include_in_project = fields.Boolean('Include in Project', default=True)
    
    # Computed fields
    total_cost = fields.Monetary('Total Cost', compute='_compute_total_cost', currency_field='currency_id')
    
    @api.depends('estimated_quantity', 'unit_cost')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.estimated_quantity * line.unit_cost


class ConstructionTemplateBOQCustomization(models.TransientModel):
    """BOQ customization line"""
    _name = 'construction.template.boq.customization'
    _description = 'Construction Template BOQ Customization'

    wizard_id = fields.Many2one('construction.template.customization.wizard', required=True, ondelete='cascade')
    boq_template_id = fields.Many2one('construction.boq.template', required=True)
    
    # Customizable fields
    name = fields.Char('BOQ Item Name', required=True)
    code = fields.Char('BOQ Code', required=True)
    quantity = fields.Float('Quantity', default=1.0)
    unit_cost = fields.Monetary('Unit Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')
    
    # Control fields
    include_in_project = fields.Boolean('Include in Project', default=True)
    
    # Computed fields
    total_cost = fields.Monetary('Total Cost', compute='_compute_total_cost', currency_field='currency_id')
    
    @api.depends('quantity', 'unit_cost')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.quantity * line.unit_cost


class ConstructionTemplateMilestoneCustomization(models.TransientModel):
    """Milestone customization line"""
    _name = 'construction.template.milestone.customization'
    _description = 'Construction Template Milestone Customization'

    wizard_id = fields.Many2one('construction.template.customization.wizard', required=True, ondelete='cascade')
    milestone_template_id = fields.Many2one('construction.milestone.template', required=True)
    
    # Customizable fields
    name = fields.Char('Milestone Name', required=True)
    days_from_start = fields.Integer('Days from Start', default=0)
    payment_percentage = fields.Float('Payment Percentage')
    
    # Control fields
    include_in_project = fields.Boolean('Include in Project', default=True)
    
    # Computed fields
    scheduled_date = fields.Date('Scheduled Date', compute='_compute_scheduled_date')
    
    @api.depends('wizard_id.start_date', 'days_from_start')
    def _compute_scheduled_date(self):
        for line in self:
            if line.wizard_id.start_date:
                line.scheduled_date = line.wizard_id.start_date + timedelta(days=line.days_from_start)
            else:
                line.scheduled_date = False