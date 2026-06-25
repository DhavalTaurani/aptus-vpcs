# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    
    # Progressive payment fields
    has_progressive_payment = fields.Boolean(
        string='Has Progressive Payment',
        compute='_compute_has_progressive_payment',
        store=True,
        help='Whether this order uses progressive payment terms'
    )
    payment_milestone_ids = fields.One2many(
        'sale.order.payment.milestone',
        'sale_order_id',
        string='Payment Milestones',
        help='Payment milestones for this order'
    )
    milestone_count = fields.Integer(
        string='Milestone Count',
        compute='_compute_milestone_count',
        help='Number of payment milestones'
    )
    
    # Milestone amounts
    total_milestone_amount = fields.Monetary(
        string='Total Milestone Amount',
        compute='_compute_milestone_amounts',
        store=True,
        help='Total amount of all milestones'
    )
    invoiced_milestone_amount = fields.Monetary(
        string='Invoiced Milestone Amount',
        compute='_compute_milestone_amounts',
        store=True,
        help='Amount of invoiced milestones'
    )
    paid_milestone_amount = fields.Monetary(
        string='Paid Milestone Amount',
        compute='_compute_milestone_amounts',
        store=True,
        help='Amount of paid milestones'
    )
    
    # Progress tracking
    milestone_progress = fields.Float(
        string='Milestone Progress (%)',
        compute='_compute_milestone_progress',
        help='Overall milestone completion progress'
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    
    @api.depends('payment_term_id.is_progressive')
    def _compute_has_progressive_payment(self):
        """Check if order uses progressive payment terms"""
        for order in self:
            order.has_progressive_payment = (
                order.payment_term_id and 
                order.payment_term_id.is_progressive
            )

    @api.depends('payment_milestone_ids')
    def _compute_milestone_count(self):
        """Compute number of milestones"""
        for order in self:
            order.milestone_count = len(order.payment_milestone_ids)

    @api.depends('payment_milestone_ids.amount', 'payment_milestone_ids.state', 'payment_milestone_ids.sub_milestone_ids.amount', 'payment_milestone_ids.sub_milestone_ids.state', 'payment_milestone_ids.invoice_id.payment_state', 'payment_milestone_ids.invoice_id.amount_residual')
    def _compute_milestone_amounts(self):
        """Compute milestone amounts by state including sub-milestones"""
        for order in self:
            milestones = order.payment_milestone_ids
            order.total_milestone_amount = sum(milestones.mapped('amount'))
            
            # Calculate invoiced amount from both milestones and sub-milestones
            invoiced_amount = 0.0
            paid_amount = 0.0
            
            for milestone in milestones:
                if milestone.sub_milestone_ids:
                    # For milestones with sub-milestones, count sub-milestone amounts
                    invoiced_subs = milestone.sub_milestone_ids.filtered(lambda s: s.state == 'invoiced')
                    invoiced_amount += sum(invoiced_subs.mapped('amount'))
                else:
                    # For milestones without sub-milestones
                    if milestone.state in ('invoiced', 'paid'):
                        invoiced_amount += milestone.amount
                    if milestone.state == 'paid':
                        paid_amount += milestone.amount
            
            # Calculate paid amounts from invoice payments
            for milestone in milestones:
                if milestone.invoice_id and milestone.invoice_id.state == 'posted':
                    # Calculate paid amount based on invoice total - residual
                    invoice_paid = milestone.invoice_id.amount_total - milestone.invoice_id.amount_residual
                    if invoice_paid > 0:
                        paid_amount += invoice_paid
            
            order.invoiced_milestone_amount = invoiced_amount
            order.paid_milestone_amount = paid_amount

    @api.depends('payment_milestone_ids.progress_percentage', 'payment_milestone_ids.sub_milestone_ids.state')
    def _compute_milestone_progress(self):
        """Compute overall milestone progress including sub-milestones"""
        for order in self:
            milestones = order.payment_milestone_ids
            if milestones:
                total_weighted_progress = 0.0
                total_amount = sum(milestones.mapped('amount'))
                
                for milestone in milestones:
                    if milestone.sub_milestone_ids:
                        # For milestones with sub-milestones, calculate progress based on sub-milestone completion
                        completed_subs = milestone.sub_milestone_ids.filtered(lambda s: s.state in ('completed', 'invoiced'))
                        total_subs = len(milestone.sub_milestone_ids)
                        if total_subs > 0:
                            sub_progress = (len(completed_subs) / total_subs) * 100.0
                            total_weighted_progress += sub_progress * milestone.amount
                        else:
                            total_weighted_progress += milestone.progress_percentage * milestone.amount
                    else:
                        # For regular milestones, use their progress percentage
                        total_weighted_progress += milestone.progress_percentage * milestone.amount
                
                order.milestone_progress = (
                    total_weighted_progress / total_amount if total_amount else 0.0
                )
            else:
                order.milestone_progress = 0.0

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    
    @api.onchange('payment_term_id')
    def _onchange_payment_term_id(self):
        """Handle payment term changes"""
        # Only call super if the method exists
        if hasattr(super(), '_onchange_payment_term_id'):
            result = super()._onchange_payment_term_id()
        else:
            result = {}
        
        if self.payment_term_id and self.payment_term_id.is_progressive:
            # Generate milestones when progressive payment term is selected
            self._generate_payment_milestones()
        else:
            # Clear milestones if non-progressive payment term is selected
            self.payment_milestone_ids = [(5, 0, 0)]
        
        return result

    @api.onchange('amount_total')
    def _onchange_amount_total(self):
        """Update milestone amounts when order total changes"""
        if self.has_progressive_payment and self.payment_milestone_ids:
            for milestone in self.payment_milestone_ids:
                milestone.calculate_amount()

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    
    def _generate_payment_milestones(self):
        """Generate payment milestones based on payment term"""
        if not self.payment_term_id or not self.payment_term_id.is_progressive:
            return
        
        # Clear existing milestones
        self.payment_milestone_ids = [(5, 0, 0)]
        
        # Get milestone lines from payment term
        milestone_lines = self.payment_term_id.line_ids.filtered('is_milestone')
        if not milestone_lines:
            return
        
        # Create milestone instances
        milestone_vals = []
        for line in milestone_lines.sorted(lambda l: (l.sequence, l.nb_days, l.id)):
            # Calculate planned date
            planned_date = False
            if self.date_order:
                from dateutil.relativedelta import relativedelta
                planned_date = self.date_order.date() + relativedelta(days=line.nb_days)
            
            # Calculate amount
            amount = 0.0
            if line.value == 'percent' and self.amount_total:
                amount = self.amount_total * (line.value_amount / 100.0)
            elif line.value == 'fixed':
                amount = line.value_amount
            
            milestone_vals.append((0, 0, {
                'payment_term_line_id': line.id,
                'milestone_name': line.milestone_display_name or str(line.milestone_type).replace('_', ' ').title(),
                'percentage': line.value_amount if line.value == 'percent' else 0.0,
                'amount': amount,
                'planned_date': planned_date,
                'sequence': line.sequence,
                'description': getattr(line, 'milestone_description', ''),
                'required_documents': getattr(line, 'required_documents', ''),
                'state': 'draft',
            }))
            
            # Create sub-milestones if applicable
            if line.allow_sub_milestones and line.sub_milestone_template_ids:
                # Sub-milestones will be created by the milestone model
                pass
        
        self.payment_milestone_ids = milestone_vals
        
        # Generate sub-milestones for milestones that support them
        self._generate_sub_milestones()

    def _generate_sub_milestones(self):
        """Generate sub-milestones for applicable milestones"""
        for milestone in self.payment_milestone_ids:
            if (milestone.payment_term_line_id.allow_sub_milestones and 
                milestone.payment_term_line_id.sub_milestone_template_ids):
                
                sub_milestone_vals = []
                for sub_template in milestone.payment_term_line_id.sub_milestone_template_ids.sorted('sequence'):
                    # Calculate planned date for sub-milestone
                    planned_date = milestone.planned_date
                    
                    sub_milestone_vals.append((0, 0, {
                        'name': sub_template.name,
                        'percentage': sub_template.percentage,
                        'planned_date': planned_date,
                        'sequence': sub_template.sequence,
                        'description': sub_template.description,
                        'state': 'draft',
                    }))
                
                milestone.sub_milestone_ids = sub_milestone_vals

    def regenerate_payment_milestones(self):
        """Regenerate payment milestones (useful after payment term changes)"""
        if self.state not in ('draft', 'sent'):
            raise ValidationError(_(
                'Payment milestones can only be regenerated for draft or sent orders'
            ))
        
        self._generate_payment_milestones()
        return True

    def _create_milestone_invoice(self, milestone):
        """Create invoice for a specific milestone"""
        self.ensure_one()
        milestone.ensure_one()
        
        if milestone.state != 'ready':
            raise ValidationError(_('Only ready milestones can be invoiced'))
        
        # Create invoice
        invoice_vals = self._prepare_milestone_invoice_vals(milestone)
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Create invoice lines
        invoice_line_vals = self._prepare_milestone_invoice_line_vals(milestone, invoice)
        self.env['account.move.line'].create(invoice_line_vals)
        
        return invoice

    def _prepare_milestone_invoice_vals(self, milestone):
        """Prepare invoice values for milestone"""
        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_origin': self.name,
            'invoice_date': fields.Date.today(),
            'ref': f"{self.name} - {milestone.milestone_name}",
            'company_id': self.company_id.id,
        }

    def _prepare_milestone_invoice_line_vals(self, milestone, invoice):
        """Prepare invoice line values for milestone"""
        # Link to all sale order lines to ensure proper invoice tracking
        sale_line_ids = [(6, 0, self.order_line.ids)] if self.order_line else []
        
        return {
            'move_id': invoice.id,
            'name': f"{milestone.milestone_name} ({milestone.percentage}%)",
            'quantity': 1.0,
            'price_unit': milestone.amount,
            'account_id': self._get_milestone_invoice_account().id,
            'milestone_id': milestone.id,
            'sale_line_ids': sale_line_ids,  # Link to sale order lines
        }

    def _get_milestone_invoice_account(self):
        """Get account for milestone invoice lines"""
        # Use the first order line's account or default income account
        if self.order_line:
            return self.order_line[0].product_id.property_account_income_id or \
                    self.order_line[0].product_id.categ_id.property_account_income_categ_id
        
        # Fallback to company's default income account
        return self.company_id.account_sale_tax_id.account_id

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    
    def action_view_milestones(self):
        """Open milestones view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Milestones'),
            'res_model': 'sale.order.payment.milestone',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
            }
        }

    def action_create_milestone_invoice(self):
        """Open wizard to create milestone invoice"""
        self.ensure_one()
        ready_milestones = self.payment_milestone_ids.filtered(lambda m: m.state == 'ready')
        
        if not ready_milestones:
            raise ValidationError(_('No ready milestones found for invoicing'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Milestone Invoice'),
            'res_model': 'milestone.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_milestone_ids': [(6, 0, ready_milestones.ids)],
            }
        }

    def action_milestone_dashboard(self):
        """Open milestone dashboard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Milestone Dashboard'),
            'res_model': 'sale.order.payment.milestone',
            'view_mode': 'kanban,list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
                'group_by': 'state',
            }
        }
    
    def action_view_all_milestones(self):
        """Open unified view of all milestones and sub-milestones"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('All Milestones'),
            'res_model': 'sale.order.payment.milestone',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
                'create': False,
            }
        }

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------
    
    def action_confirm(self):
        """Override to handle milestone generation on confirmation"""
        result = super().action_confirm()
        
        # Generate milestones for confirmed orders with progressive payment terms
        for order in self:
            if order.has_progressive_payment and not order.payment_milestone_ids:
                order._generate_payment_milestones()
        
        return result

    def write(self, vals):
        """Override to handle payment term changes"""
        result = super().write(vals)
        
        # Regenerate milestones if payment term changed
        if 'payment_term_id' in vals:
            for order in self:
                if (order.state in ('draft', 'sent') and 
                    order.has_progressive_payment):
                    order._generate_payment_milestones()
        
        return result