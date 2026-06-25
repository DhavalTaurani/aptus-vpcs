# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    # Sub-milestone tracking
    sub_milestone_id = fields.Many2one(
        'sale.order.payment.milestone.sub',
        string='Sub-milestone',
        help='Related sub-milestone for this invoice line'
    )


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    
    # Progressive payment fields
    is_milestone_invoice = fields.Boolean(
        string='Is Milestone Invoice',
        default=False,
        help='Whether this invoice is for a progressive payment milestone'
    )
    milestone_ids = fields.One2many(
        'sale.order.payment.milestone',
        'invoice_id',
        string='Related Milestones',
        help='Milestones related to this invoice'
    )
    milestone_count = fields.Integer(
        string='Milestone Count',
        compute='_compute_milestone_count',
        help='Number of related milestones'
    )
    
    # Source sale order for milestone tracking
    source_sale_order_id = fields.Many2one(
        'sale.order',
        string='Source Sale Order',
        help='Source sale order for milestone invoice'
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    
    @api.depends('milestone_ids')
    def _compute_milestone_count(self):
        """Compute number of related milestones"""
        for move in self:
            move.milestone_count = len(move.milestone_ids)

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------
    


    def action_post(self):
        """Override to update milestone status when invoice is posted"""
        result = super().action_post()
        
        # Update milestone status for milestone invoices
        for move in self:
            if move.is_milestone_invoice and move.milestone_ids:
                for milestone in move.milestone_ids:
                    if milestone.state == 'ready':
                        milestone.write({
                            'state': 'invoiced',
                            'actual_date': fields.Date.today(),
                            'progress_percentage': 100.0  # Mark as 100% complete when invoiced
                        })
        
        return result

    def _post(self, soft=True):
        """Override to trigger payment status update after posting"""
        result = super()._post(soft)
        # Update milestone payment status after posting
        self.update_milestone_payment_status()
        return result

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """Override to handle milestone status when invoice is reversed"""
        result = super()._reverse_moves(default_values_list, cancel)
        
        # Revert milestone status for milestone invoices
        for move in self:
            if move.is_milestone_invoice and move.milestone_ids:
                for milestone in move.milestone_ids:
                    if milestone.state == 'invoiced':
                        milestone.write({'state': 'ready'})
        
        return result

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    
    @api.model
    def create_milestone_invoice(self, milestone_ids, invoice_vals=None):
        """Create invoice for specific milestones"""
        if not milestone_ids:
            raise ValidationError(_('No milestones provided for invoice creation'))
        
        milestones = self.env['sale.order.payment.milestone'].browse(milestone_ids)
        
        # Validate milestones
        for milestone in milestones:
            if milestone.state != 'ready':
                raise ValidationError(_(
                    'Milestone "%s" is not ready for invoicing (current state: %s)'
                ) % (milestone.milestone_name, milestone.state))
            
            # For milestones with sub-milestones, check if at least one is completed
            if milestone.sub_milestone_ids:
                completed_subs = milestone.sub_milestone_ids.filtered(
                    lambda s: s.state == 'completed'
                )
                if not completed_subs:
                    raise ValidationError(_(
                        'Milestone "%s" has no completed sub-milestones. '
                        'At least one sub-milestone must be completed before invoicing.'
                    ) % milestone.milestone_name)
        
        # Get sale order (all milestones should be from same order)
        sale_orders = milestones.mapped('sale_order_id')
        if len(sale_orders) > 1:
            raise ValidationError(_('All milestones must be from the same sale order'))
        
        sale_order = sale_orders[0]
        
        # Get immediate payment term for milestone invoices
        immediate_payment_term = self.env.ref('account.account_payment_term_immediate', raise_if_not_found=False)
        if not immediate_payment_term:
            # Fallback: find or create immediate payment term
            immediate_payment_term = self.env['account.payment.term'].search([
                ('name', '=', 'Immediate Payment')
            ], limit=1)
            if not immediate_payment_term:
                immediate_payment_term = self.env['account.payment.term'].create({
                    'name': 'Immediate Payment',
                    'line_ids': [(0, 0, {'value': 'balance', 'nb_days': 0})]
                })
        
        # Prepare invoice values
        default_invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': sale_order.partner_id.id,
            'currency_id': sale_order.currency_id.id,
            'invoice_payment_term_id': immediate_payment_term.id,  # Use immediate payment for milestones
            'invoice_origin': sale_order.name,
            'invoice_date': fields.Date.today(),
            'company_id': sale_order.company_id.id,
            'is_milestone_invoice': True,
            'source_sale_order_id': sale_order.id,
        }
        
        if invoice_vals:
            default_invoice_vals.update(invoice_vals)
        
        # Create invoice
        invoice = self.create(default_invoice_vals)
        
        # Create invoice lines for each milestone with dedicated sale order lines
        for milestone in milestones:
            if milestone.sub_milestone_ids:
                # Create invoice lines only for completed sub-milestones
                completed_subs = milestone.sub_milestone_ids.filtered(
                    lambda s: s.state == 'completed'
                )
                for sub_milestone in completed_subs:
                    # Create dedicated sale order line for this sub-milestone
                    sale_line = self._create_milestone_sale_line(sale_order, milestone, sub_milestone)
                    
                    invoice_line_vals = {
                        'move_id': invoice.id,
                        'name': f"{milestone.milestone_name} - {sub_milestone.name}",
                        'quantity': 1.0,
                        'price_unit': sub_milestone.amount,
                        'milestone_id': milestone.id,
                        'account_id': self._get_milestone_account(milestone).id,
                        'sale_line_ids': [(6, 0, [sale_line.id])],
                        'tax_ids': [(5, 0, 0)],
                    }
                    
                    # Add analytic distribution from project if available
                    analytic_distribution = self._get_milestone_analytic_distribution(sale_order)
                    if analytic_distribution:
                        invoice_line_vals['analytic_distribution'] = analytic_distribution
                    
                    # Add product if available from original sale order
                    if sale_order.order_line:
                        first_line = sale_order.order_line[0]
                        if first_line.product_id:
                            invoice_line_vals.update({
                                'product_id': first_line.product_id.id,
                                'product_uom_id': first_line.product_uom_id.id,
                            })
                    
                    self.env['account.move.line'].create(invoice_line_vals)
            else:
                # Create dedicated sale order line for milestone without sub-milestones
                sale_line = self._create_milestone_sale_line(sale_order, milestone)
                
                invoice_line_vals = {
                    'move_id': invoice.id,
                    'name': f"{milestone.milestone_name} - {sale_order.name}",
                    'quantity': 1.0,
                    'price_unit': milestone.amount,
                    'milestone_id': milestone.id,
                    'account_id': self._get_milestone_account(milestone).id,
                    'sale_line_ids': [(6, 0, [sale_line.id])],
                    'tax_ids': [(5, 0, 0)],
                }
                
                # Add analytic distribution from project if available
                analytic_distribution = self._get_milestone_analytic_distribution(sale_order)
                if analytic_distribution:
                    invoice_line_vals['analytic_distribution'] = analytic_distribution
                
                # Add product if available from original sale order
                if sale_order.order_line:
                    first_line = sale_order.order_line[0]
                    if first_line.product_id:
                        invoice_line_vals.update({
                            'product_id': first_line.product_id.id,
                            'product_uom_id': first_line.product_uom_id.id,
                        })
                
                self.env['account.move.line'].create(invoice_line_vals)
        
        # Link milestones to invoice
        milestones.write({'invoice_id': invoice.id})
        
        # Update original sale order lines to reflect invoiced amounts
        self._update_original_sale_lines(sale_order, milestones)
        
        return invoice
    
    @api.model
    def create_sub_milestone_invoice(self, sub_milestone_id, sale_order_id):
        """Create invoice for a specific sub-milestone"""
        sub_milestone = self.env['sale.order.payment.milestone.sub'].browse(sub_milestone_id)
        sale_order = self.env['sale.order'].browse(sale_order_id)
        
        if sub_milestone.state != 'completed':
            raise ValidationError(_('Sub-milestone must be completed before invoicing'))
        
        # Get immediate payment term
        immediate_payment_term = self.env.ref('account.account_payment_term_immediate', raise_if_not_found=False)
        if not immediate_payment_term:
            immediate_payment_term = self.env['account.payment.term'].search([
                ('name', '=', 'Immediate Payment')
            ], limit=1)
        
        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': sale_order.partner_id.id,
            'currency_id': sale_order.currency_id.id,
            'invoice_payment_term_id': immediate_payment_term.id,
            'invoice_origin': sale_order.name,
            'invoice_date': fields.Date.today(),
            'company_id': sale_order.company_id.id,
            'is_milestone_invoice': True,
            'source_sale_order_id': sale_order.id,
        }
        
        invoice = self.create(invoice_vals)
        
        # Create dedicated sale order line
        sale_line = self._create_sub_milestone_sale_line(sale_order, sub_milestone)
        
        # Create invoice line
        invoice_line_vals = {
            'move_id': invoice.id,
            'name': f"{sub_milestone.name} - {sale_order.name}",
            'quantity': 1.0,
            'price_unit': sub_milestone.amount,
            'sub_milestone_id': sub_milestone.id,
            'account_id': self._get_milestone_account_for_sub(sale_order).id,
            'sale_line_ids': [(6, 0, [sale_line.id])],
            'tax_ids': [(5, 0, 0)],
        }
        
        # Add analytic distribution
        if sub_milestone.analytic_account_id:
            invoice_line_vals['analytic_distribution'] = {sub_milestone.analytic_account_id.id: 100}
        
        # Add product info from original sale order
        if sale_order.order_line:
            first_line = sale_order.order_line[0]
            if first_line.product_id:
                invoice_line_vals.update({
                    'product_id': first_line.product_id.id,
                    'product_uom_id': first_line.product_uom_id.id,
                })
        
        self.env['account.move.line'].create(invoice_line_vals)
        
        # Update original sale order lines
        self._update_original_sale_lines_for_sub(sale_order, sub_milestone)
        
        return invoice
    
    def _create_sub_milestone_sale_line(self, sale_order, sub_milestone):
        """Create dedicated sale order line for sub-milestone invoicing"""
        original_line = sale_order.order_line[0] if sale_order.order_line else None
        
        sale_line_vals = {
            'order_id': sale_order.id,
            'name': sub_milestone.name,
            'product_uom_qty': 1.0,
            'price_unit': sub_milestone.amount,
            'sequence': 9999,
        }
        
        if original_line:
            sale_line_vals.update({
                'product_id': original_line.product_id.id if original_line.product_id else False,
                'product_uom_id': original_line.product_uom_id.id if original_line.product_uom_id else False,
                'tax_ids': [(6, 0, original_line.tax_ids.ids)],
            })
        
        return self.env['sale.order.line'].create(sale_line_vals)
    
    def _get_milestone_account_for_sub(self, sale_order):
        """Get account for sub-milestone invoice line"""
        if sale_order.order_line:
            for line in sale_order.order_line:
                if line.product_id:
                    account = (line.product_id.property_account_income_id or 
                            line.product_id.categ_id.property_account_income_categ_id)
                    if account:
                        return account
        
        return self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            ('account_type', '=', 'income')
        ], limit=1)
    
    def _update_original_sale_lines_for_sub(self, sale_order, sub_milestone):
        """Update original sale order lines for sub-milestone invoice"""
        if not sale_order.order_line:
            return
        
        original_lines = sale_order.order_line.filtered(lambda l: l.sequence < 9999)
        total_original = sum(original_lines.mapped(lambda l: l.price_unit * l.product_uom_qty))
        
        for line in original_lines:
            line_total = line.price_unit * line.product_uom_qty
            line_proportion = line_total / total_original if total_original else 0
            deduction = sub_milestone.amount * line_proportion
            
            new_line_total = line_total - deduction
            if new_line_total > 0:
                new_price_unit = new_line_total / line.product_uom_qty if line.product_uom_qty else 0
                line.write({'price_unit': new_price_unit})
            else:
                line.write({'price_unit': 0.01})

    def _get_milestone_account(self, milestone):
        """Get account for milestone invoice line"""
        sale_order = milestone.sale_order_id
        
        # Try to get account from sale order lines
        if sale_order.order_line:
            for line in sale_order.order_line:
                if line.product_id:
                    account = (line.product_id.property_account_income_id or 
                            line.product_id.categ_id.property_account_income_categ_id)
                    if account:
                        return account
        
        # Fallback to company default income account
        return (self.company_id.account_sale_tax_id.account_id or
                self.env['account.account'].search([
                    ('company_id', '=', self.company_id.id),
                    ('account_type', '=', 'income')
                ], limit=1))
    
    def _get_milestone_analytic_distribution(self, sale_order):
        """Get analytic distribution for milestone invoice lines from linked project"""
        analytic_distribution = {}
        
        # Check if sale order has a linked project (from sale_project module)
        if hasattr(sale_order, 'project_id') and sale_order.project_id:
            project = sale_order.project_id
            if project.account_id:
                analytic_distribution[project.account_id.id] = 100
        
        # Check if sale order has analytic account directly
        elif hasattr(sale_order, 'account_id') and sale_order.account_id:
            analytic_distribution[sale_order.account_id.id] = 100
        
        # Check if any sale order line has project_id (from sale_project module)
        elif sale_order.order_line:
            for line in sale_order.order_line:
                if hasattr(line, 'project_id') and line.project_id and line.project_id.account_id:
                    analytic_distribution[line.project_id.account_id.id] = 100
                    break
        
        return analytic_distribution
    
    def _create_milestone_sale_line(self, sale_order, milestone, sub_milestone=None):
        """Create dedicated sale order line for milestone invoicing"""
        # Get original sale line as template
        original_line = sale_order.order_line[0] if sale_order.order_line else None
        
        if sub_milestone:
            line_name = f"{milestone.milestone_name} - {sub_milestone.name}"
            amount = sub_milestone.amount
        else:
            line_name = milestone.milestone_name
            amount = milestone.amount
            
        if original_line and original_line.tax_ids:
            tax_percent = sum(original_line.tax_ids.mapped('amount'))
            price_unit = amount / (1 + (tax_percent / 100))
        else:
            price_unit = amount
        
        # Create new sale order line
        sale_line_vals = {
            'order_id': sale_order.id,
            'name': line_name,
            'product_uom_qty': 1.0,
            'price_unit': price_unit,
            'sequence': 9999,  # Put milestone lines at the end
        }
        
        # Copy product and account info from original line if available
        if original_line:
            sale_line_vals.update({
                'product_id': original_line.product_id.id if original_line.product_id else False,
                'product_uom_id': original_line.product_uom_id.id if original_line.product_uom_id else False,
                'tax_ids': [(6, 0, original_line.tax_ids.ids)],
            })
            # Copy project_id if available for analytic tracking
            if hasattr(original_line, 'project_id') and original_line.project_id:
                sale_line_vals['project_id'] = original_line.project_id.id
        
        return self.env['sale.order.line'].create(sale_line_vals)
    
    def _update_original_sale_lines(self, sale_order, milestones):
        """Update original sale order lines to reflect remaining amounts"""
        if not sale_order.order_line:
            return
        
        # Get original lines (sequence < 9999)
        original_lines = sale_order.order_line.filtered(lambda l: l.sequence < 9999)
        if not original_lines:
            return
        
        # Calculate total original amount
        total_original = sum(original_lines.mapped(lambda l: l.price_unit * l.product_uom_qty))
        
        # Calculate current milestone invoice amount (tax excluded)
        current_invoice_amount = 0.0
        for milestone in milestones:
            if milestone.sub_milestone_ids:
                # Sum only completed sub-milestones
                completed_subs = milestone.sub_milestone_ids.filtered(lambda s: s.state == 'completed')
                for sub in completed_subs:
                    # Deduct tax if original line has tax
                    if original_lines[0].tax_ids:
                        tax_percent = sum(original_lines[0].tax_ids.mapped('amount'))
                        current_invoice_amount += sub.amount / (1 + tax_percent / 100)
                    else:
                        current_invoice_amount += sub.amount
            else:
                # Deduct tax if original line has tax
                if original_lines[0].tax_ids:
                    tax_percent = sum(original_lines[0].tax_ids.mapped('amount'))
                    current_invoice_amount += milestone.amount / (1 + tax_percent / 100)
                else:
                    current_invoice_amount += milestone.amount
        
        # Deduct current invoice amount proportionally from original lines
        for line in original_lines:
            line_total = line.price_unit * line.product_uom_qty
            line_proportion = line_total / total_original if total_original else 0
            deduction = current_invoice_amount * line_proportion
            
            new_line_total = line_total - deduction
            if new_line_total > 0:
                new_price_unit = new_line_total / line.product_uom_qty if line.product_uom_qty else 0
                line.write({
                    'price_unit': new_price_unit
                })
            else:
                # Set to minimal amount to keep line visible
                line.write({
                    'price_unit': 0.01
                })

    def update_milestone_payment_status(self):
        """Update milestone payment status based on invoice payment"""
        for move in self:
            if move.is_milestone_invoice and move.milestone_ids:
                if move.payment_state == 'paid':
                    # Mark milestones as paid with 100% progress
                    for milestone in move.milestone_ids:
                        if milestone.state == 'invoiced':
                            milestone.write({
                                'state': 'paid',
                                'progress_percentage': 100.0
                            })
                        # Also update sub-milestones that were invoiced
                        invoiced_subs = milestone.sub_milestone_ids.filtered(lambda s: s.state == 'invoiced')
                        if invoiced_subs:
                            # Sub-milestones don't have 'paid' state, but we can track via parent milestone
                            pass  # Payment tracking is handled via parent milestone
                elif move.payment_state in ('not_paid', 'partial'):
                    # Revert to invoiced if payment is reversed
                    move.milestone_ids.filtered(
                        lambda m: m.state == 'paid'
                    ).write({
                        'state': 'invoiced',
                        'progress_percentage': 100.0  # Keep progress at 100% when invoiced
                    })
                
                # Trigger recomputation of sale order amounts
                sale_orders = move.milestone_ids.mapped('sale_order_id')
                if sale_orders:
                    sale_orders._compute_milestone_amounts()
                    sale_orders._compute_milestone_progress()

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    
    def action_view_milestones(self):
        """Open related milestones view"""
        self.ensure_one()
        if not self.milestone_ids:
            raise ValidationError(_('No milestones found for this invoice'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Milestones'),
            'res_model': 'sale.order.payment.milestone',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.milestone_ids.ids)],
            'context': {'create': False}
        }

    def action_view_source_sale_order(self):
        """Open source sale order"""
        self.ensure_one()
        if not self.source_sale_order_id:
            raise ValidationError(_('No source sale order found'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Source Sale Order'),
            'res_model': 'sale.order',
            'res_id': self.source_sale_order_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    # -------------------------------------------------------------------------
    # CRON METHODS
    # -------------------------------------------------------------------------
    
    @api.model
    def _cron_update_milestone_payment_status(self):
        """Cron job to update milestone payment status"""
        milestone_invoices = self.search([
            ('is_milestone_invoice', '=', True),
            ('milestone_ids', '!=', False),
            ('state', '=', 'posted')
        ])
        
        for invoice in milestone_invoices:
            invoice.update_milestone_payment_status()
        
        return True