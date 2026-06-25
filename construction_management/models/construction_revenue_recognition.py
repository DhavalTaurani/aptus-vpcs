# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ConstructionRevenueRecognition(models.Model):
    _name = "construction.revenue.recognition"
    _description = "Construction Revenue Recognition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char("Name", required=True, tracking=True)
    project_id = fields.Many2one(
        "project.project",
        "Project",
        required=True,
        domain="[('is_construction', '=', True)]",
        tracking=True,
    )
    invoice_ids = fields.Many2many(
        "account.move",
        "construction_revenue_recognition_move_rel",
        "revenue_recognition_id",
        "move_id",
        string="Invoices",
        readonly=True,
        copy=False,
    )
    invoice_count = fields.Integer(
        compute="_compute_invoice_count", string="Invoice Count"
    )
    income_account_id = fields.Many2one(
        "account.account",
        string="Income Account",
        domain="[('account_type', '=', 'income'), ('company_ids', 'in', [company_id])]",
        default=lambda self: self._get_default_income_account(),
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # Recognition method
    recognition_method = fields.Selection(
        [
            ("percentage_completion", "Percentage of Completion"),
            ("milestone", "Milestone Based"),
            ("completed_contract", "Completed Contract"),
        ],
        string="Recognition Method",
        required=True,
        tracking=True,
    )

    # Calculation fields
    total_contract_value = fields.Monetary(
        "Total Contract Value", currency_field="currency_id"
    )
    total_estimated_cost = fields.Monetary(
        "Total Estimated Cost", currency_field="currency_id"
    )
    actual_cost_to_date = fields.Monetary(
        "Actual Cost to Date", currency_field="currency_id"
    )
    percentage_complete = fields.Float(
        "Percentage Complete", compute="_compute_percentage_complete", store=True
    )

    milestone_ids = fields.Many2many(
        "construction.subcontractor.milestone",
        string="Related Milestones",
        relation="cons_rev_rec_sub_mil_rel",
    )

    # Revenue amounts
    revenue_to_recognize = fields.Monetary(
        "Revenue to Recognize",
        compute="_compute_revenue_to_recognize",
        store=True,
        currency_field="currency_id",
    )
    revenue_recognized = fields.Monetary(
        "Revenue Recognized", currency_field="currency_id"
    )
    revenue_remaining = fields.Monetary(
        "Revenue Remaining",
        compute="_compute_revenue_remaining",
        store=True,
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(related="project_id.currency_id", readonly=True)
    partner_id = fields.Many2one(
        related="project_id.partner_id", 
        string="Customer", 
        store=True, 
        readonly=True
    )

    @api.model
    def _get_default_income_account(self):
        """Get default income account based on Odoo 17.0 standards"""
        try:
            # Method 1: Try to get from product category (most common approach in Odoo)
            # First, try to find a service product category with income account
            service_category = self.env["product.category"].search(
                [("name", "ilike", "service")], limit=1
            )

            if service_category and service_category.property_account_income_categ_id:
                return service_category.property_account_income_categ_id

            # Method 2: Try to get from any product category with income account
            category_with_income = self.env["product.category"].search(
                [("property_account_income_categ_id", "!=", False)], limit=1
            )

            if category_with_income:
                return category_with_income.property_account_income_categ_id

            # Method 3: Fallback - search for any income account in the company
            income_account = self.env["account.account"].search(
                [
                    ("account_type", "=", "income"),
                    ("company_id", "=", self.env.company.id),
                    ("deprecated", "=", False),
                ],
                limit=1,
            )

            return income_account

        except Exception:
            # If anything fails, return False (no default)
            return False

    @api.onchange("company_id")
    def _onchange_company_id(self):
        """Update income account when company changes"""
        if self.company_id and not self.income_account_id:
            self.income_account_id = self._get_default_income_account()

    @api.depends("actual_cost_to_date", "total_estimated_cost")
    def _compute_percentage_complete(self):
        for record in self:
            if record.total_estimated_cost and record.total_estimated_cost > 0:
                record.percentage_complete = (
                    record.actual_cost_to_date / record.total_estimated_cost
                ) * 100
            else:
                record.percentage_complete = 0.0

    @api.depends(
        "total_contract_value",
        "percentage_complete",
        "recognition_method",
        "milestone_ids.amount",
        "milestone_ids.is_completed",
    )
    def _compute_revenue_to_recognize(self):
        for record in self:
            if record.recognition_method == "percentage_completion":
                record.revenue_to_recognize = (
                    record.total_contract_value * record.percentage_complete
                ) / 100
            elif record.recognition_method == "milestone":
                record.revenue_to_recognize = sum(
                    record.milestone_ids.filtered("is_completed").mapped("amount")
                )
            else:
                record.revenue_to_recognize = (
                    0.0  # Completed Contract will be handled differently
                )

    @api.depends("revenue_to_recognize", "revenue_recognized")
    def _compute_revenue_remaining(self):
        for record in self:
            record.revenue_remaining = (
                record.revenue_to_recognize - record.revenue_recognized
            )

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    def action_view_invoices(self):
        self.ensure_one()
        result = {
            "name": _("Invoices"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.invoice_ids.ids)],
        }
        if len(self.invoice_ids) == 1:
            result["view_mode"] = "form"
            result["res_id"] = self.invoice_ids.id
        return result

    def action_recognize_revenue(self):
        """Create customer invoice for revenue recognition"""
        self.ensure_one()
        if self.revenue_to_recognize <= self.revenue_recognized:
            raise UserError(_("No revenue to recognize or already fully recognized."))

        amount_to_recognize = self.revenue_to_recognize - self.revenue_recognized

        if not self.project_id.partner_id:
            raise UserError(_("Project must have a customer associated."))

        # Get income account
        income_account = self.income_account_id
        if not income_account:
            income_account = self.env["account.account"].search(
                [
                    ("account_type", "=", "income"),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )

        if not income_account:
            raise UserError(
                _("Please define an income account for revenue recognition.")
            )

        # Create customer invoice
        journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.company_id.id)], limit=1
        )
        if not journal:
            raise UserError(_("Please define a sale journal for the company."))

        move_vals = {
            "ref": _("Revenue Recognition for %s") % self.name,
            "move_type": "out_invoice",
            "journal_id": journal.id,
            "partner_id": self.project_id.partner_id.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": _("Revenue Recognition - %s") % self.name,
                        "account_id": income_account.id,
                        "price_unit": amount_to_recognize,
                        "quantity": 1,
                        "analytic_distribution": (
                            {self.project_id.analytic_account_id.id: 100}
                            if self.project_id.analytic_account_id
                            else {}
                        ),
                    },
                )
            ],
        }
        move = self.env["account.move"].create(move_vals)

        # Link the invoice to this revenue recognition record
        self.write(
            {
                "revenue_recognized": self.revenue_recognized + amount_to_recognize,
                "invoice_ids": [(4, move.id)],
            }
        )

        # Post the invoice automatically
        move.action_post()

        # Log activity
        self.message_post(
            body=_("Revenue recognition invoice created: %s for amount %s")
            % (move.name, amount_to_recognize),
            message_type="notification",
        )

        return {
            "name": _("Customer Invoice"),
            "view_mode": "form",
            "res_model": "account.move",
            "res_id": move.id,
            "type": "ir.actions.act_window",
            "target": "current",
        }

    def action_recognize_revenue_bulk(self):
        """Bulk revenue recognition from list view - group by customer"""
        if not self:
            raise UserError(_("Please select revenue recognition records to process."))

        # Group by customer
        customer_groups = {}
        for record in self:
            if record.revenue_to_recognize <= record.revenue_recognized:
                continue  # Skip already recognized

            if not record.project_id.partner_id:
                raise UserError(
                    _("Project '%s' must have a customer associated.")
                    % record.project_id.name
                )

            customer = record.project_id.partner_id
            if customer not in customer_groups:
                customer_groups[customer] = []
            customer_groups[customer].append(record)

        if not customer_groups:
            raise UserError(_("No revenue to recognize for selected records."))

        created_invoices = []

        for customer, records in customer_groups.items():
            # Create one invoice per customer
            journal = self.env["account.journal"].search(
                [("type", "=", "sale"), ("company_id", "=", records[0].company_id.id)],
                limit=1,
            )
            if not journal:
                raise UserError(_("Please define a sale journal for the company."))

            invoice_lines = []
            total_amount = 0

            for record in records:
                amount_to_recognize = (
                    record.revenue_to_recognize - record.revenue_recognized
                )
                if amount_to_recognize <= 0:
                    continue

                # Get income account
                income_account = record.income_account_id
                if not income_account:
                    income_account = self.env["account.account"].search(
                        [
                            ("account_type", "=", "income"),
                            ("company_id", "=", record.company_id.id),
                        ],
                        limit=1,
                    )

                if not income_account:
                    raise UserError(
                        _("Please define an income account for revenue recognition.")
                    )

                invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "name": _("Revenue Recognition - %s") % record.name,
                            "account_id": income_account.id,
                            "price_unit": amount_to_recognize,
                            "quantity": 1,
                            "analytic_distribution": (
                                {record.project_id.analytic_account_id.id: 100}
                                if record.project_id.analytic_account_id
                                else {}
                            ),
                        },
                    )
                )
                total_amount += amount_to_recognize

            if not invoice_lines:
                continue

            # Create grouped invoice
            move_vals = {
                "ref": _("Bulk Revenue Recognition - %s") % customer.name,
                "move_type": "out_invoice",
                "journal_id": journal.id,
                "partner_id": customer.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": invoice_lines,
            }
            move = self.env["account.move"].create(move_vals)

            # Update revenue recognition records
            for record in records:
                amount_to_recognize = (
                    record.revenue_to_recognize - record.revenue_recognized
                )
                if amount_to_recognize > 0:
                    record.write(
                        {
                            "revenue_recognized": record.revenue_recognized
                            + amount_to_recognize,
                            "invoice_ids": [(4, move.id)],
                        }
                    )

                    # Log activity
                    record.message_post(
                        body=_(
                            "Bulk revenue recognition invoice created: %s for amount %s"
                        )
                        % (move.name, amount_to_recognize),
                        message_type="notification",
                    )

            # Post the invoice
            move.action_post()
            created_invoices.append(move)

        if len(created_invoices) == 1:
            return {
                "name": _("Customer Invoice"),
                "view_mode": "form",
                "res_model": "account.move",
                "res_id": created_invoices[0].id,
                "type": "ir.actions.act_window",
                "target": "current",
            }
        else:
            return {
                "name": _("Customer Invoices"),
                "view_mode": "list,form",
                "res_model": "account.move",
                "domain": [("id", "in", [inv.id for inv in created_invoices])],
                "type": "ir.actions.act_window",
                "target": "current",
            }
