# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ConstructionSubcontractor(models.Model):
    _name = "construction.subcontractor"
    _description = "Construction Subcontractor"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("Name", required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        "Vendor",
        required=True,
        domain=[("is_company", "=", True)],
        tracking=True,
    )
    project_id = fields.Many2one(
        "project.project",
        "Project",
        required=True,
        domain="[('is_construction', '=', True)]",
        tracking=True,
    )

    # Contract details
    contract_value = fields.Monetary(
        "Contract Value", currency_field="currency_id", tracking=True
    )
    contract_start_date = fields.Date("Contract Start Date", tracking=True)
    contract_end_date = fields.Date("Contract End Date", tracking=True)
    retention_percentage = fields.Float("Retention %", default=5.0, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("billed", "Billed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    # Work packages
    task_ids = fields.Many2many(
        "project.task",
        string="Assigned Tasks",
        domain="[('project_id', '=', 'project_id')]",
    )
    task_count = fields.Integer("Task Count", compute="_compute_task_count")
    invoice_ids = fields.One2many("account.move", "subcontractor_id", string="Invoices")
    invoice_count = fields.Integer("Invoice Count", compute="_compute_invoice_count")
    milestone_ids = fields.One2many(
        "construction.subcontractor.milestone", "subcontractor_id", string="Milestones"
    )

    @api.depends("task_ids")
    def _compute_task_count(self):
        for sub in self:
            sub.task_count = len(sub.task_ids)

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for sub in self:
            sub.invoice_count = len(sub.invoice_ids)

    # Progress tracking
    progress_percentage = fields.Float(
        "Progress %",
        compute="_compute_progress",
        store=True,
        help="Weighted average progress of assigned tasks",
    )
    invoiced_amount = fields.Monetary(
        "Invoiced Amount",
        compute="_compute_financials",
        currency_field="currency_id",
        help="Total amount invoiced to this subcontractor",
    )
    paid_amount = fields.Monetary(
        "Paid Amount",
        compute="_compute_financials",
        currency_field="currency_id",
        help="Total amount paid to this subcontractor",
    )
    retention_amount = fields.Monetary(
        "Retention Amount",
        compute="_compute_financials",
        currency_field="currency_id",
        help="Total retention amount held",
    )

    # Performance Analytics
    on_time_completion_rate = fields.Float(
        "On-Time Completion Rate", compute="_compute_performance_analytics", store=True
    )
    quality_score = fields.Float(
        "Quality Score", compute="_compute_performance_analytics", store=True
    )

    currency_id = fields.Many2one(related="project_id.currency_id", readonly=True)

    @api.depends("task_ids.physical_progress", "task_ids.boq_value")
    def _compute_progress(self):
        for sub in self:
            total_weighted_progress = 0.0
            total_boq_value = 0.0
            for task in sub.task_ids.filtered(
                lambda t: t.is_boq_item and t.boq_value > 0
            ):
                total_weighted_progress += (
                    task.physical_progress / 100.0
                ) * task.boq_value
                total_boq_value += task.boq_value

            if total_boq_value > 0:
                sub.progress_percentage = (
                    total_weighted_progress / total_boq_value
                ) * 100
            else:
                sub.progress_percentage = 0.0

    @api.depends(
        "invoice_ids.amount_total",
        "invoice_ids.payment_state",
        "invoice_ids.amount_residual",
    )
    def _compute_financials(self):
        for sub in self:
            invoiced_amount = 0.0
            paid_amount = 0.0
            retention_amount = 0.0

            for invoice in sub.invoice_ids:
                if invoice.move_type == "in_invoice" and invoice.state == "posted":
                    invoiced_amount += invoice.amount_total
                    if invoice.payment_state in ("paid", "in_payment"):
                        paid_amount += invoice.amount_total - invoice.amount_residual
                    # Assuming retention is part of the invoice and needs to be calculated
                    # This is a simplified example, actual retention logic might be more complex
                    retention_amount += invoice.amount_total * (
                        sub.retention_percentage / 100.0
                    )

            sub.invoiced_amount = invoiced_amount
            sub.paid_amount = paid_amount
            sub.retention_amount = retention_amount

    @api.constrains("retention_percentage")
    def _check_retention_percentage(self):
        for sub in self:
            if sub.retention_percentage < 0 or sub.retention_percentage > 100:
                raise ValidationError(
                    _("Retention percentage must be between 0 and 100.")
                )

    def action_activate(self):
        self.write({"state": "active"})

    def action_complete(self):
        self.write({"state": "completed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_view_tasks(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tasks"),
            "res_model": "project.task",
            "view_mode": "list,form",
            "domain": [("id", "in", self.task_ids.ids)],
            "context": {"default_project_id": self.project_id.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.invoice_ids.ids)],
            "context": {"default_subcontractor_id": self.id},
        }

    def action_create_bill(self):
        self.ensure_one()
        # Create a new vendor bill
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_id.id,
                "subcontractor_id": self.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.name,
                            "quantity": 1,
                            "price_unit": self.contract_value,
                        },
                    )
                ],
            }
        )
        self.write({"state": "billed"})
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bill"),
            "res_model": "account.move",
            "res_id": invoice.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends("task_ids.stage_id", "task_ids.date_deadline")
    def _compute_performance_analytics(self):
        for sub in self:
            # On-Time Completion Rate - following Odoo 17 standard patterns
            completed_tasks = sub.task_ids.filtered(
                lambda t: t.stage_id and t.stage_id.fold
            )
            if not completed_tasks:
                sub.on_time_completion_rate = 0.0
            else:
                on_time_tasks = completed_tasks.filtered(
                    lambda t: t.date_deadline
                    and t.write_date
                    and t.write_date.date()
                    <= (
                        t.date_deadline.date()
                        if hasattr(t.date_deadline, "date")
                        else t.date_deadline
                    )
                )
                sub.on_time_completion_rate = (
                    len(on_time_tasks) / len(completed_tasks)
                ) * 100

            # Quality Score (placeholder logic)
            # In a real implementation, this would be based on quality inspections or other metrics
            sub.quality_score = 85.0  # Default quality score


class ConstructionSubcontractorMilestone(models.Model):
    _name = "construction.subcontractor.milestone"
    _description = "Subcontractor Milestone"
    _order = "sequence, target_date"

    name = fields.Char("Milestone Name", required=True)
    sequence = fields.Integer("Sequence", default=10)
    subcontractor_id = fields.Many2one(
        "construction.subcontractor", "Subcontractor", required=True, ondelete="cascade"
    )
    project_id = fields.Many2one(
        related="subcontractor_id.project_id",
        string="Project",
        store=True,
        readonly=True,
    )
    amount = fields.Monetary("Amount", currency_field="currency_id", required=True)
    target_date = fields.Date("Target Date")
    completion_date = fields.Date("Completion Date")
    is_completed = fields.Boolean("Completed", default=False)
    description = fields.Text("Description")

    currency_id = fields.Many2one(related="subcontractor_id.currency_id", readonly=True)

    def action_mark_completed(self):
        """Mark milestone as completed"""
        self.write({"is_completed": True, "completion_date": fields.Date.today()})

    def action_mark_incomplete(self):
        """Mark milestone as incomplete"""
        self.write({"is_completed": False, "completion_date": False})
