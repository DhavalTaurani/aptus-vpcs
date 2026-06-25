# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MilestoneInvoiceWizard(models.TransientModel):
    _name = 'milestone.invoice.wizard'
    _description = 'Milestone Invoice Creation Wizard'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        help='Sale order for milestone invoicing'
    )
    milestone_ids = fields.Many2many(
        'sale.order.payment.milestone',
        string='Milestones',
        required=True,
        help='Milestones to include in invoice'
    )
    invoice_date = fields.Date(
        string='Invoice Date',
        default=fields.Date.today,
        required=True,
        help='Date for the invoice'
    )
    create_separate_invoices = fields.Boolean(
        string='Create Separate Invoices',
        default=False,
        help='Create separate invoice for each milestone'
    )
    
    # Computed fields
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        currency_field='currency_id',
        help='Total amount of selected milestones'
    )
    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        string='Currency'
    )
    milestone_count = fields.Integer(
        string='Milestone Count',
        compute='_compute_milestone_count',
        help='Number of selected milestones'
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    
    @api.depends('milestone_ids')
    def _compute_total_amount(self):
        """Compute total amount of selected milestones"""
        for wizard in self:
            wizard.total_amount = sum(wizard.milestone_ids.mapped('amount'))

    @api.depends('milestone_ids')
    def _compute_milestone_count(self):
        """Compute number of selected milestones"""
        for wizard in self:
            wizard.milestone_count = len(wizard.milestone_ids)

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    
    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Filter milestones based on sale order"""
        if self.sale_order_id:
            ready_milestones = self.sale_order_id.payment_milestone_ids.filtered(
                lambda m: m.state == 'ready'
            )
            return {
                'domain': {
                    'milestone_ids': [('id', 'in', ready_milestones.ids)]
                }
            }
        else:
            return {
                'domain': {
                    'milestone_ids': [('id', '=', False)]
                }
            }

    # -------------------------------------------------------------------------
    # VALIDATION METHODS
    # -------------------------------------------------------------------------
    
    @api.constrains('milestone_ids')
    def _check_milestone_state(self):
        """Validate that all milestones are ready for invoicing"""
        for wizard in self:
            non_ready_milestones = wizard.milestone_ids.filtered(
                lambda m: m.state != 'ready'
            )
            if non_ready_milestones:
                milestone_names = ', '.join(non_ready_milestones.mapped('milestone_name'))
                raise ValidationError(_(
                    'The following milestones are not ready for invoicing: %s'
                ) % milestone_names)

    @api.constrains('milestone_ids', 'sale_order_id')
    def _check_milestone_sale_order(self):
        """Validate that all milestones belong to the selected sale order"""
        for wizard in self:
            if wizard.milestone_ids and wizard.sale_order_id:
                wrong_order_milestones = wizard.milestone_ids.filtered(
                    lambda m: m.sale_order_id != wizard.sale_order_id
                )
                if wrong_order_milestones:
                    raise ValidationError(_(
                        'All selected milestones must belong to the selected sale order'
                    ))

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    
    def action_create_invoice(self):
        """Create invoice(s) for selected milestones"""
        self.ensure_one()
        
        if not self.milestone_ids:
            raise ValidationError(_('Please select at least one milestone'))
        
        if self.create_separate_invoices:
            return self._create_separate_invoices()
        else:
            return self._create_single_invoice()

    def _create_single_invoice(self):
        """Create single invoice for all selected milestones"""
        invoice_vals = {
            'invoice_date': self.invoice_date,
        }
        
        invoice = self.env['account.move'].with_context(default_move_type="out_invoice").create_milestone_invoice(
            self.milestone_ids.ids,
            invoice_vals
        )
        
        return self._return_invoice_action(invoice)

    def _create_separate_invoices(self):
        """Create separate invoice for each milestone"""
        invoices = self.env['account.move']
        
        for milestone in self.milestone_ids:
            invoice_vals = {
                'invoice_date': self.invoice_date,
                'ref': f"{self.sale_order_id.name} - {milestone.milestone_name}",
            }
            
            invoice = self.env['account.move'].with_context(default_move_type="out_invoice").create_milestone_invoice(
                [milestone.id],
                invoice_vals
            )
            invoices |= invoice
        
        if len(invoices) == 1:
            return self._return_invoice_action(invoices)
        else:
            return self._return_invoice_list_action(invoices)

    def _return_invoice_action(self, invoice):
        """Return action to view single invoice"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Milestone Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _return_invoice_list_action(self, invoices):
        """Return action to view multiple invoices"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Milestone Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
            'target': 'current',
        }

    def action_preview_invoice(self):
        """Preview invoice before creation"""
        self.ensure_one()
        
        # Create a preview of what the invoice would look like
        preview_data = {
            'sale_order': self.sale_order_id.name,
            'partner': self.sale_order_id.partner_id.name,
            'invoice_date': self.invoice_date,
            'milestones': [],
            'total_amount': self.total_amount,
            'currency': self.currency_id.name,
        }
        
        for milestone in self.milestone_ids:
            preview_data['milestones'].append({
                'name': milestone.milestone_name,
                'percentage': milestone.percentage,
                'amount': milestone.amount,
                'type': milestone.milestone_type,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice Preview'),
            'res_model': 'milestone.invoice.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_preview_data': str(preview_data),
                'default_wizard_id': self.id,
            }
        }

    # -------------------------------------------------------------------------
    # DEFAULT METHODS
    # -------------------------------------------------------------------------
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        defaults = super().default_get(fields_list)
        
        # Get sale order from context
        if 'sale_order_id' in fields_list:
            sale_order_id = self.env.context.get('default_sale_order_id')
            if sale_order_id:
                defaults['sale_order_id'] = sale_order_id
        
        # Get milestones from context
        if 'milestone_ids' in fields_list:
            milestone_ids = self.env.context.get('default_milestone_ids')
            if milestone_ids:
                defaults['milestone_ids'] = milestone_ids
        
        return defaults


class MilestoneInvoicePreview(models.TransientModel):
    _name = 'milestone.invoice.preview'
    _description = 'Milestone Invoice Preview'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    
    wizard_id = fields.Many2one(
        'milestone.invoice.wizard',
        string='Wizard',
        required=True
    )
    preview_data = fields.Text(
        string='Preview Data',
        help='JSON data for preview'
    )

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    
    def action_confirm_create(self):
        """Confirm and create the invoice"""
        self.ensure_one()
        return self.wizard_id.action_create_invoice()

    def action_back_to_wizard(self):
        """Go back to wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Milestone Invoice'),
            'res_model': 'milestone.invoice.wizard',
            'res_id': self.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }