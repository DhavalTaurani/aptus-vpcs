# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ConstructionTask(models.Model):
    _inherit = "project.task"

    # BOQ identification
    is_boq_item = fields.Boolean(
        "Is BOQ Item",
        default=False,
        help="Check if this task represents a Bill of Quantities item",
    )
    boq_code = fields.Char(
        "BOQ Code", index=True, help="Unique BOQ identification code"
    )
    cost_code_id = fields.Many2one(
        "construction.cost.code",
        "Cost Code",
        help="Construction cost code for categorization",
    )
    product_id = fields.Many2one(
        "product.product", "Product", help="Product associated with this task", compute='_compute_product_variant_id'
    )
    subcontractor_id = fields.Many2one(
        "construction.subcontractor",
        "Assigned Subcontractor",
        help="Subcontractor assigned to this BOQ item",
    )

    # Quantity tracking
    estimated_quantity = fields.Float(
        "Estimated Quantity",
        digits="Product Unit of Measure",
        help="Original estimated quantity",
    )
    revised_quantity = fields.Float(
        "Revised Quantity",
        digits="Product Unit of Measure",
        help="Revised quantity after changes",
    )
    actual_quantity = fields.Float(
        "Actual Quantity",
        digits="Product Unit of Measure",
        help="Actual quantity consumed/completed",
    )
    quantity_variance = fields.Float(
        "Quantity Variance",
        compute="_compute_quantity_variance",
        digits="Product Unit of Measure",
        help="Difference between revised and actual quantity",
    )
    quantity_variance_percentage = fields.Float(
        "Quantity Variance %",
        compute="_compute_quantity_variance",
        help="Quantity variance as percentage",
    )

    unit_of_measure_id = fields.Many2one(
        "uom.uom", "Unit of Measure", help="Unit of measure for quantities"
    )

    # Cost calculations
    unit_cost = fields.Monetary(
        "Unit Cost", currency_field="currency_id", help="Cost per unit of measure"
    )
    boq_value = fields.Monetary(
        "BOQ Value",
        compute="_compute_boq_value",
        store=True,
        currency_field="currency_id",
        help="Total BOQ value (revised quantity × unit cost)",
    )
    committed_cost = fields.Monetary(
        "Committed Cost",
        compute="_compute_committed_cost",
        currency_field="currency_id",
        help="Committed cost from purchase orders",
    )
    actual_cost = fields.Monetary(
        "Actual Cost",
        compute="_compute_actual_cost",
        store=True,
        currency_field="currency_id",
        help="Actual cost from invoices and stock moves",
    )
    cost_variance = fields.Monetary(
        "Cost Variance",
        compute="_compute_cost_variance",
        store=True,
        currency_field="currency_id",
        help="Difference between BOQ value and actual cost",
    )
    cost_variance_percentage = fields.Float(
        "Cost Variance %",
        compute="_compute_cost_variance",
        store=True,  # Set to True to be consistent with cost_variance
        help="Cost variance as percentage of BOQ value",
    )

    # Progress tracking
    physical_progress = fields.Float(
        "Physical Progress (%)", 
        compute="_compute_physical_progress",
        store=True,
        help="Physical completion percentage"
    )
    cost_progress = fields.Float(
        "Cost Progress (%)",
        compute="_compute_cost_progress",
        help="Cost progress based on actual vs budgeted costs",
    )

    # BOQ specific fields
    boq_description = fields.Text(
        "BOQ Description", help="Detailed description of the BOQ item"
    )
    boq_specification = fields.Text(
        "Specification", help="Technical specifications for the BOQ item"
    )

    # Approval workflow
    boq_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("revised", "Revised"),
            ("billed", "Billed"),
        ],
        string="BOQ Status",
        default="draft",
        tracking=True,
    )

    # Computed field to show appropriate state for BOQ items
    display_state = fields.Char(
        string="Status",
        compute="_compute_display_state",
        help="Shows BOQ state for BOQ items, stage for regular tasks",
    )

    is_billed = fields.Boolean(
        string="Billed",
        compute="_compute_is_billed",
        store=True,
        help="Indicates if the BOQ item has been fully billed.",
    )

    @api.depends('cost_code_id')
    def _compute_product_variant_id(self):
        for p in self:
            p.product_id = p.cost_code_id.product_template_id and p.cost_code_id.product_template_id.product_variant_id.id or False

    @api.depends("is_boq_item", "boq_state", "stage_id")
    def _compute_display_state(self):
        """Compute display state based on whether it's a BOQ item or regular task"""
        for task in self:
            if task.is_boq_item:
                # For BOQ items, show the BOQ state
                state_dict = dict(task._fields["boq_state"].selection)
                task.display_state = state_dict.get(task.boq_state, task.boq_state)
            else:
                # For regular tasks, show the stage name
                task.display_state = task.stage_id.name if task.stage_id else "No Stage"

    @api.depends("purchase_line_ids.invoice_lines.move_id.state")
    def _compute_is_billed(self):
        for task in self:
            if not task.is_boq_item:
                task.is_billed = False
                continue

            billed_qty = 0
            for po_line in task.purchase_line_ids:
                for invoice_line in po_line.invoice_lines:
                    if invoice_line.move_id.state == "posted":
                        billed_qty += invoice_line.quantity

            total_qty = task.revised_quantity or task.estimated_quantity
            task.is_billed = billed_qty >= total_qty if total_qty > 0 else False
            if task.is_billed and task.boq_state != "billed":
                task.boq_state = "billed"
                task._sync_boq_state_to_stage()

    @api.onchange("boq_state")
    def _onchange_boq_state(self):
        """Sync BOQ state to stage when changed"""
        if self.is_boq_item:
            self._sync_boq_state_to_stage()

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle BOQ item initialization"""
        tasks = super().create(vals_list)
        for task in tasks:
            if task.is_boq_item:
                # Ensure BOQ state is set and synced to stage
                if not task.boq_state:
                    task.boq_state = "draft"
                task._sync_boq_state_to_stage()
        return tasks

    # Related fields for easy access
    construction_type = fields.Selection(
        related="project_id.construction_type",
        string="Construction Type",
        readonly=True,
    )
    currency_id = fields.Many2one(related="project_id.currency_id", readonly=True)

    purchase_line_ids = fields.One2many(
        "purchase.order.line",
        "boq_task_id",
        string="Purchase Order Lines",
        help="Purchase order lines related to this BOQ item",
    )
    purchase_order_count = fields.Integer(
        "Purchase Order Count", compute="_compute_purchase_order_count", store=True
    )
    stock_move_count = fields.Integer(
        "Stock Move Count", compute="_compute_stock_move_count"
    )

    @api.depends("purchase_line_ids")
    def _compute_purchase_order_count(self):
        for task in self:
            task.purchase_order_count = len(task.purchase_line_ids)

    @api.depends("purchase_line_ids.move_ids")
    def _compute_stock_move_count(self):
        for task in self:
            task.stock_move_count = len(task.purchase_line_ids.mapped("move_ids"))

    @api.depends("revised_quantity", "actual_quantity")
    def _compute_quantity_variance(self):
        """Compute quantity variance and percentage"""
        for task in self:
            task.quantity_variance = task.revised_quantity - task.actual_quantity
            if task.revised_quantity:
                task.quantity_variance_percentage = (
                    task.quantity_variance / task.revised_quantity
                ) * 100
            else:
                task.quantity_variance_percentage = 0.0

    @api.depends("revised_quantity", "unit_cost")
    def _compute_boq_value(self):
        """Compute BOQ value from revised quantity and unit cost"""
        for task in self:
            if task.is_boq_item:
                task.boq_value = task.revised_quantity * task.unit_cost
            else:
                task.boq_value = 0.0

    @api.depends("purchase_line_ids.price_subtotal", "purchase_line_ids.order_id.state")
    def _compute_committed_cost(self):
        """Compute committed cost from purchase orders"""
        for task in self:
            committed_cost = 0.0
            # Filter for confirmed purchase orders
            confirmed_po_lines = task.purchase_line_ids.filtered(
                lambda l: l.order_id.state in ["purchase", "done"]
            )
            if confirmed_po_lines:
                committed_cost = sum(confirmed_po_lines.mapped("price_subtotal"))
            task.committed_cost = committed_cost

    def _compute_actual_cost(self):
        """Compute actual cost from analytic lines"""
        for task in self:
            if task.project_id.account_id:
                # Search for analytic lines related to this task
                analytic_lines = self.env["account.analytic.line"].search(
                    [
                        ("account_id", "=", task.project_id.account_id.id),
                        ("task_id", "=", task.id),
                        ("amount", "<", 0),  # Costs are negative in analytic lines
                    ]
                )
                task.actual_cost = abs(sum(analytic_lines.mapped("amount")))
            else:
                task.actual_cost = 0.0

    @api.depends('boq_state')
    def _compute_physical_progress(self):
        for record in self:
            if record.boq_state == 'draft':
                record.physical_progress = 0.0
            elif record.boq_state == 'submitted':
                record.physical_progress = 33.333
            elif record.boq_state == 'approved':
                record.physical_progress = 66.666
            elif record.boq_state == 'billed':
                record.physical_progress = 100.0
            else:
                record.physical_progress = 0.0

    @api.depends("boq_value", "actual_cost")
    def _compute_cost_variance(self):
        """Compute cost variance and percentage"""
        for task in self:
            task.cost_variance = task.boq_value - task.actual_cost
            if task.boq_value:
                task.cost_variance_percentage = (
                    task.cost_variance / task.boq_value
                ) * 100
            else:
                task.cost_variance_percentage = 0.0

    @api.depends("boq_value", "actual_cost")
    def _compute_cost_progress(self):
        """Compute cost progress based on actual vs budgeted costs"""
        for task in self:
            if task.boq_value:
                task.cost_progress = (task.actual_cost / task.boq_value) * 100
            else:
                task.cost_progress = 0.0

    @api.onchange("is_boq_item")
    def _onchange_is_boq_item(self):
        """Set default values when BOQ item is checked"""
        if self.is_boq_item:
            if not self.boq_code:
                # Generate a default BOQ code
                sequence = self.env["ir.sequence"].next_by_code("construction.boq.code")
                if sequence:
                    self.boq_code = sequence
            # Set initial BOQ state and sync to stage
            if not self.boq_state:
                self.boq_state = "draft"
            self._sync_boq_state_to_stage()

    @api.onchange("cost_code_id")
    def _onchange_cost_code_id(self):
        """Set default values from cost code"""
        if self.cost_code_id:
            self.unit_of_measure_id = self.cost_code_id.default_uom_id
            if not self.unit_cost:
                self.unit_cost = self.cost_code_id.standard_cost

    @api.onchange("estimated_quantity")
    def _onchange_estimated_quantity(self):
        """Set revised quantity to estimated quantity if not set"""
        if self.estimated_quantity and not self.revised_quantity:
            self.revised_quantity = self.estimated_quantity

    @api.constrains("estimated_quantity", "revised_quantity", "actual_quantity")
    def _check_quantities(self):
        """Validate quantities"""
        for task in self:
            if task.is_boq_item:
                if (
                    task.estimated_quantity < 0
                    or task.revised_quantity < 0
                    or task.actual_quantity < 0
                ):
                    raise ValidationError(
                        "Quantities cannot be negative for BOQ items."
                    )

    @api.constrains("unit_cost")
    def _check_unit_cost(self):
        """Validate unit cost"""
        for task in self:
            if task.is_boq_item and task.unit_cost < 0:
                raise ValidationError("Unit cost cannot be negative for BOQ items.")

    @api.constrains("physical_progress")
    def _check_physical_progress(self):
        """Validate physical progress"""
        for task in self:
            if task.physical_progress < 0 or task.physical_progress > 100:
                raise ValidationError(
                    "Physical progress must be between 0 and 100 percent."
                )

    @api.constrains("boq_code")
    def _check_boq_code_unique(self):
        """Ensure BOQ code is unique within project"""
        for task in self:
            if task.is_boq_item and task.boq_code:
                existing = self.search(
                    [
                        ("id", "!=", task.id),
                        ("project_id", "=", task.project_id.id),
                        ("boq_code", "=", task.boq_code),
                        ("is_boq_item", "=", True),
                    ]
                )
                if existing:
                    raise ValidationError(
                        f"BOQ code '{task.boq_code}' already exists in this project."
                    )

    def action_submit_boq(self):
        """Submit BOQ item for approval"""
        self.ensure_one()
        if not self.is_boq_item:
            raise ValidationError("Only BOQ items can be submitted for approval.")
        self.boq_state = "submitted"
        self._sync_boq_state_to_stage()

        # Create activity for approval
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            summary=f"BOQ Approval Required: {self.boq_code}",
            note=f"BOQ item {self.boq_code} has been submitted for approval.",
            user_id=self.project_id.user_id.id or self.env.user.id,
        )

    def action_approve_boq(self):
        """Approve BOQ item"""
        self.ensure_one()
        if not self.is_boq_item:
            raise ValidationError("Only BOQ items can be approved.")
        self.boq_state = "approved"
        self._sync_boq_state_to_stage()

        # Mark related activities as done
        activities = self.activity_ids.filtered(
            lambda a: a.activity_type_id.name == "Todo"
        )
        activities.action_done()

    def action_reject_boq(self):
        """Reject BOQ item"""
        self.ensure_one()
        if not self.is_boq_item:
            raise ValidationError("Only BOQ items can be rejected.")
        self.boq_state = "rejected"
        self._sync_boq_state_to_stage()

        # Mark related activities as done
        activities = self.activity_ids.filtered(
            lambda a: a.activity_type_id.name == "Todo"
        )
        activities.action_done()

    def action_reset_to_draft(self):
        """Reset BOQ item to draft"""
        self.ensure_one()
        self.boq_state = "draft"
        self._sync_boq_state_to_stage()

    def _sync_boq_state_to_stage(self):
        """Sync BOQ state to appropriate project stage"""
        if not self.is_boq_item or not self.project_id:
            return

        # Map BOQ states to stage names (you can customize this mapping)
        state_stage_mapping = {
            "draft": "Draft",
            "submitted": "In Review",
            "approved": "Approved",
            "rejected": "Rejected",
            "revised": "Revision",
            "billed": "Done",
        }

        target_stage_name = state_stage_mapping.get(self.boq_state)
        if not target_stage_name:
            return

        # Find or create the appropriate stage
        stage = self.env["project.task.type"].search(
            [
                ("project_ids", "in", [self.project_id.id]),
                ("name", "=", target_stage_name),
            ],
            limit=1,
        )

        if not stage:
            # Create the stage if it doesn't exist
            stage = self.env["project.task.type"].create(
                {
                    "name": target_stage_name,
                    "project_ids": [(4, self.project_id.id)],
                    "sequence": len(self.project_id.type_ids) + 1,
                    "fold": target_stage_name in ["Rejected", "Done"],
                }
            )

        self.stage_id = stage.id

    def action_view_purchase_orders(self):
        """View purchase orders related to this BOQ item"""
        # This will be implemented when purchase integration is added
        return {
            "type": "ir.actions.act_window",
            "name": f"Purchase Orders - {self.name}",
            "res_model": "purchase.order.line",
            "view_mode": "list,form",
            "domain": [("boq_task_id", "=", self.id)],
            "context": {"default_boq_task_id": self.id},
        }

    def action_view_stock_moves(self):
        """View stock moves related to this BOQ item"""
        action = self.env.ref("stock.stock_move_action").read()[0]
        action["domain"] = [("purchase_line_id", "in", self.purchase_line_ids.ids)]
        return action

    def _cron_generate_purchase_requirements(self):
        """Cron job to generate purchase requirements for approved BOQ items"""
        approved_tasks = self.search(
            [
                ("is_boq_item", "=", True),
                ("boq_state", "=", "approved"),
                ("purchase_order_count", "=", 0),  # No PO lines yet
            ]
        )

        for task in approved_tasks:
            if not (task.revised_quantity or task.estimated_quantity) > 0:
                continue

            if not task.cost_code_id or not task.cost_code_id.product_template_id:
                continue

            product = task.cost_code_id.product_template_id.product_variant_id
            if not product.seller_ids:
                continue

            # Create a purchase requisition/agreement (or a draft PO)
            # For simplicity, we'll create a draft purchase order here
            vendor = product.seller_ids[0].partner_id
            po_vals = {
                "partner_id": vendor.id,
                "state": "draft",  # Create as a draft RFQ
            }
            po = self.env["purchase.order"].create(po_vals)

            po_line_vals = {
                "order_id": po.id,
                "product_id": product.id,
                "name": product.name,
                "product_qty": task.revised_quantity or task.estimated_quantity,
                "price_unit": task.unit_cost,
                "product_uom_id": product.uom_id.id,
                "date_planned": fields.Date.today(),
                "construction_project_id": task.project_id.id,
                "boq_task_id": task.id,
                "cost_code_id": task.cost_code_id.id,
            }
            self.env["purchase.order.line"].create(po_line_vals)
