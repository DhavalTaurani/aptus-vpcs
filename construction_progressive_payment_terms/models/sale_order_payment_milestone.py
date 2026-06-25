# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderPaymentMilestone(models.Model):
    _name = 'sale.order.payment.milestone'
    _description = 'Sale Order Payment Milestone'
    _order = 'sale_order_id, sequence, id'
    _rec_name = 'milestone_name'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    
    # Core relationships
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade',
        help='Related sale order'
    )
    payment_term_line_id = fields.Many2one(
        'account.payment.term.line',
        string='Payment Term Line',
        help='Related payment term line milestone'
    )
    
    # Milestone identification
    milestone_name = fields.Char(
        string='Milestone Name',
        required=True,
        help='Name of the milestone'
    )
    milestone_type = fields.Selection(
        related='payment_term_line_id.milestone_type',
        string='Milestone Type',
        store=True,
        help='Type of milestone'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence for ordering milestones'
    )
    
    # Amount and percentage
    percentage = fields.Float(
        string='Percentage (%)',
        digits=(5, 2),
        help='Percentage of total order amount'
    )
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        help='Milestone amount in order currency'
    )
    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        string='Currency',
        store=True
    )
    
    # Date management
    planned_date = fields.Date(
        string='Planned Date',
        help='Planned completion date for milestone'
    )
    actual_date = fields.Date(
        string='Actual Date',
        help='Actual completion date'
    )
    
    # State management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled')
    ], string='Status',
        default='draft',
        help='Status of the milestone')
    
    # Progress tracking
    progress_percentage = fields.Float(
        string='Progress (%)',
        digits=(5, 2),
        compute='_compute_progress_percentage',
        store=True,
        help='Completion progress percentage'
    )
    
    # Invoice tracking
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        help='Related invoice for this milestone'
    )
    invoice_line_ids = fields.One2many(
        'account.move.line',
        'milestone_id',
        string='Invoice Lines',
        help='Invoice lines related to this milestone'
    )
    
    # Description and requirements
    description = fields.Html(
        string='Description',
        help='Detailed description of milestone requirements'
    )
    required_documents = fields.Text(
        string='Required Documents',
        help='Documents required for milestone completion'
    )
    
    # Analytic tracking
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        compute='_compute_analytic_account_id',
        store=True,
        help='Analytic account for project costing'
    )
    
    # Approval workflow
    approval_required = fields.Boolean(
        related='payment_term_line_id.approval_required',
        string='Approval Required',
        store=True
    )
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        help='User who approved the milestone'
    )
    approved_date = fields.Datetime(
        string='Approved Date',
        help='Date when milestone was approved'
    )
    
    # Sub-milestone support
    has_sub_milestones = fields.Boolean(
        string='Has Sub-milestones',
        compute='_compute_has_sub_milestones',
        help='Whether this milestone has sub-milestones'
    )
    allow_sub_milestones = fields.Boolean(
        string='Allow Sub-milestones',
        default=False,
        help='Enable sub-milestones for this milestone'
    )
    sub_milestone_ids = fields.One2many(
        'sale.order.payment.milestone.sub',
        'parent_milestone_id',
        string='Sub-milestones',
        help='Sub-milestones for this milestone'
    )
    
    # Computed fields
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
        help='Whether milestone is overdue'
    )
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_is_overdue',
        help='Number of days overdue'
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    
    @api.depends('sub_milestone_ids')
    def _compute_has_sub_milestones(self):
        """Check if milestone has sub-milestones"""
        for milestone in self:
            milestone.has_sub_milestones = bool(milestone.sub_milestone_ids)
    
    @api.depends('planned_date', 'state')
    def _compute_is_overdue(self):
        """Compute if milestone is overdue"""
        today = fields.Date.today()
        for milestone in self:
            if (milestone.planned_date and 
                milestone.planned_date < today and 
                milestone.state not in ('paid', 'cancelled')):
                milestone.is_overdue = True
                milestone.days_overdue = (today - milestone.planned_date).days
            else:
                milestone.is_overdue = False
                milestone.days_overdue = 0
    
    @api.depends('sub_milestone_ids.state', 'state')
    def _compute_progress_percentage(self):
        """Compute progress percentage based on sub-milestones or milestone state"""
        for milestone in self:
            if milestone.sub_milestone_ids:
                # Calculate progress based on sub-milestone states
                total_subs = len(milestone.sub_milestone_ids)
                if total_subs > 0:
                    completed_subs = len(milestone.sub_milestone_ids.filtered(
                        lambda s: s.state in ('completed', 'invoiced')
                    ))
                    milestone.progress_percentage = (completed_subs / total_subs) * 100.0
                else:
                    milestone.progress_percentage = 0.0
            else:
                # For milestones without sub-milestones, base on state
                if milestone.state == 'draft':
                    milestone.progress_percentage = 0.0
                elif milestone.state == 'ready':
                    milestone.progress_percentage = 50.0
                elif milestone.state in ('invoiced', 'paid'):
                    milestone.progress_percentage = 100.0
                else:
                    milestone.progress_percentage = 0.0
    
    @api.depends('sale_order_id.project_id.account_id', 'sale_order_id.order_line.project_id.account_id')
    def _compute_analytic_account_id(self):
        """Compute analytic account from linked project or sale order"""
        for milestone in self:
            analytic_account = False
            
            # Check if sale order has a linked project (from sale_project module)
            if (hasattr(milestone.sale_order_id, 'project_id') and 
                milestone.sale_order_id.project_id and 
                milestone.sale_order_id.project_id.account_id):
                analytic_account = milestone.sale_order_id.project_id.account_id
            
            # Check if sale order has analytic account directly
            elif (hasattr(milestone.sale_order_id, 'analytic_account_id') and 
                    milestone.sale_order_id.analytic_account_id):
                analytic_account = milestone.sale_order_id.analytic_account_id
            
            # Check if any sale order line has project_id (from sale_project module)
            elif milestone.sale_order_id.order_line:
                for line in milestone.sale_order_id.order_line:
                    if (hasattr(line, 'project_id') and 
                        line.project_id and 
                        line.project_id.account_id):
                        analytic_account = line.project_id.account_id
                        break
            
            milestone.analytic_account_id = analytic_account

    # -------------------------------------------------------------------------
    # CONSTRAINS METHODS
    # -------------------------------------------------------------------------
    
    @api.constrains('percentage')
    def _check_percentage_range(self):
        """Validate percentage is within valid range"""
        for milestone in self:
            if milestone.percentage < 0 or milestone.percentage > 100:
                raise ValidationError(_(
                    'Milestone percentage must be between 0 and 100. '
                    'Current value: %.2f%%'
                ) % milestone.percentage)

    @api.constrains('progress_percentage')
    def _check_progress_percentage_range(self):
        """Validate progress percentage is within valid range"""
        for milestone in self:
            if milestone.progress_percentage < 0 or milestone.progress_percentage > 100:
                raise ValidationError(_(
                    'Progress percentage must be between 0 and 100. '
                    'Current value: %.2f%%'
                ) % milestone.progress_percentage)

    @api.constrains('amount')
    def _check_amount_positive(self):
        """Ensure milestone amount is positive"""
        for milestone in self:
            if milestone.amount < 0:
                raise ValidationError(_(
                    'Milestone amount must be positive. '
                    'Current value: %s'
                ) % milestone.amount)

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    
    @api.onchange('payment_term_line_id')
    def _onchange_payment_term_line_id(self):
        """Update milestone details when payment term line changes"""
        if self.payment_term_line_id:
            self.milestone_name = self.payment_term_line_id.milestone_display_name
            self.percentage = self.payment_term_line_id.value_amount
            self.description = self.payment_term_line_id.milestone_description
            self.required_documents = self.payment_term_line_id.required_documents
            self.sequence = self.payment_term_line_id.sequence
            
            # Calculate planned date
            if self.sale_order_id and self.sale_order_id.date_order:
                from dateutil.relativedelta import relativedelta
                self.planned_date = self.sale_order_id.date_order.date() + relativedelta(
                    days=self.payment_term_line_id.nb_days
                )

    @api.onchange('percentage', 'sale_order_id')
    def _onchange_percentage(self):
        """Recalculate amount when percentage changes"""
        if self.percentage and self.sale_order_id:
            self.amount = self.sale_order_id.amount_total * (self.percentage / 100.0)
    
    @api.onchange('allow_sub_milestones')
    def _onchange_allow_sub_milestones(self):
        """Handle sub-milestone creation/removal"""
        if self.allow_sub_milestones and not self.sub_milestone_ids:
            # Create default sub-milestones for material delivery type
            if self.milestone_type == 'material_delivery':
                self.sub_milestone_ids = [
                    (0, 0, {
                        'name': 'Material Delivery - Phase 1',
                        'percentage': 50.0,
                        'sequence': 10,
                        'description': 'First phase of material delivery'
                    }),
                    (0, 0, {
                        'name': 'Material Delivery - Phase 2', 
                        'percentage': 50.0,
                        'sequence': 20,
                        'description': 'Second phase of material delivery'
                    })
                ]
        elif not self.allow_sub_milestones:
            # Clear sub-milestones when disabled
            self.sub_milestone_ids = [(5, 0, 0)]

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    
    def name_get(self):
        """Override name_get to show milestone information"""
        result = []
        for milestone in self:
            name = f"{milestone.milestone_name} ({milestone.percentage}%)"
            if milestone.sale_order_id:
                name = f"{milestone.sale_order_id.name} - {name}"
            result.append((milestone.id, name))
        return result

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    
    def action_set_ready(self):
        """Mark milestone as ready for invoicing"""
        # Check if milestone has sub-milestones
        if self.sub_milestone_ids:
            incomplete_subs = self.sub_milestone_ids.filtered(
                lambda s: s.state != 'completed'
            )
            if incomplete_subs:
                sub_names = ', '.join(incomplete_subs.mapped('name'))
                raise ValidationError(_(
                    'Cannot set milestone to ready. '
                    'Complete these sub-milestones first: %s'
                ) % sub_names)
        
        self.write({'state': 'ready'})
        return True

    def action_invoice(self):
        """Create invoice for this milestone"""
        self.ensure_one()
        if self.state != 'ready':
            raise ValidationError(_('Only ready milestones can be invoiced'))
        
        # Create invoice using sale order's invoice creation
        invoice = self.sale_order_id.with_context(default_move_type="out_invoice")._create_milestone_invoice(self)
        self.write({
            'state': 'invoiced',
            'invoice_id': invoice.id,
            'actual_date': fields.Date.today()
        })
        return invoice

    # def action_mark_paid(self):
    #     """Mark milestone as paid"""
    #     self.write({'state': 'paid'})
    #     return True

    def action_cancel(self):
        """Cancel milestone"""
        self.write({'state': 'cancelled'})
        return True

    def action_approve(self):
        """Approve milestone for payment"""
        self.ensure_one()
        if not self.approval_required:
            raise ValidationError(_('This milestone does not require approval'))
        
        self.write({
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
            'state': 'ready'
        })
        return True

    def action_reset_to_draft(self):
        """Reset milestone to draft state and handle invoice"""
        self.ensure_one()
        
        if self.invoice_id:
            # Restore original sale order line amounts before removing invoice
            self._restore_original_sale_lines()
            
            # Clear milestone reference from invoice lines first
            if self.invoice_line_ids:
                self.invoice_line_ids.write({'milestone_id': False})
            
            if self.invoice_id.state == 'draft':
                # If invoice is draft, simply unlink it
                self.invoice_id.unlink()
            elif self.invoice_id.state == 'posted':
                # Handle payments if invoice is paid
                if self.invoice_id.payment_state in ('paid', 'in_payment', 'partial'):
                    self._remove_invoice_payments(self.invoice_id)
                
                # Cancel and reset invoice to draft
                self.invoice_id.button_cancel()
                self.invoice_id.button_draft()
        
        # Reset milestone to draft
        self.write({
            'state': 'draft',
            'actual_date': False,
            'approved_by': False,
            'approved_date': False
        })
        return True
    
    def _remove_invoice_payments(self, invoice):
        """Remove payments linked to invoice when resetting to draft"""
        if not invoice or invoice.state != 'posted':
            return
        
        # Find payment moves linked to this invoice
        payment_moves = self.env['account.move'].search([
            ('line_ids.matched_debit_ids.debit_move_id', 'in', invoice.line_ids.ids),
            ('move_type', 'in', ['entry', 'in_receipt', 'out_receipt']),
            ('state', '=', 'posted')
        ])
        
        payment_moves |= self.env['account.move'].search([
            ('line_ids.matched_credit_ids.credit_move_id', 'in', invoice.line_ids.ids),
            ('move_type', 'in', ['entry', 'in_receipt', 'out_receipt']),
            ('state', '=', 'posted')
        ])
        
        # Remove reconciliation first
        for line in invoice.line_ids.filtered(lambda l: l.account_id.reconcile):
            if line.matched_debit_ids or line.matched_credit_ids:
                line.remove_move_reconcile()
        
        # Cancel and unlink payment moves
        for payment_move in payment_moves:
            if payment_move.state == 'posted':
                payment_move.button_cancel()
            payment_move.unlink()
    
    def _restore_original_sale_lines(self):
        """Restore original sale order line amounts when resetting milestone"""
        if not self.invoice_id or not self.sale_order_id:
            return
        
        # Find milestone-specific sale order lines created for this invoice
        milestone_lines = self.sale_order_id.order_line.filtered(
            lambda l: l.sequence >= 9999 and (
                self.milestone_name in l.name or 
                any(sub.name in l.name for sub in self.sub_milestone_ids)
            )
        )
        
        # Calculate total amount to restore
        restore_amount = sum(milestone_lines.mapped(lambda l: l.price_unit * l.product_uom_qty))
        
        # Set milestone-specific lines quantity to zero (can't unlink in confirmed orders)
        milestone_lines.write({'product_uom_qty': 0})
        
        # Restore original lines proportionally
        if restore_amount > 0:
            original_lines = self.sale_order_id.order_line.filtered(lambda l: l.sequence < 9999)
            if original_lines:
                # Calculate current total of original lines
                current_total = sum(original_lines.mapped(lambda l: l.price_unit * l.product_uom_qty))
                
                # Calculate what the original total should be
                target_total = current_total + restore_amount
                
                # Restore each line proportionally
                for line in original_lines:
                    current_line_total = line.price_unit * line.product_uom_qty
                    if current_total > 0:
                        line_proportion = current_line_total / current_total
                        additional_amount = restore_amount * line_proportion
                        new_line_total = current_line_total + additional_amount
                        new_price_unit = new_line_total / line.product_uom_qty if line.product_uom_qty else 0
                        line.write({'price_unit': new_price_unit})



    def update_progress(self, progress_percentage):
        """Update milestone progress"""
        self.write({'progress_percentage': progress_percentage})
        
        # Auto-set to ready if 100% complete
        if progress_percentage >= 100 and self.state == 'draft':
            self.action_set_ready()
        
        return True

    def calculate_amount(self):
        """Recalculate milestone amount based on current order total"""
        for milestone in self:
            if milestone.sale_order_id and milestone.percentage:
                milestone.amount = milestone.sale_order_id.amount_total * (milestone.percentage / 100.0)

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    
    def action_view_invoice(self):
        """Open related invoice"""
        self.ensure_one()
        if not self.invoice_id:
            raise ValidationError(_('No invoice found for this milestone'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Milestone Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_sub_milestones(self):
        """Open sub-milestones view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sub-milestones'),
            'res_model': 'sale.order.payment.milestone.sub',
            'view_mode': 'list,form',
            'domain': [('parent_milestone_id', '=', self.id)],
            'context': {
                'default_parent_milestone_id': self.id,
            }
        }
    
    def action_create_milestone_invoice(self):
        """Create invoice for this milestone directly"""
        self.ensure_one()
        if self.state != 'ready':
            raise ValidationError(_('Only ready milestones can be invoiced'))
        
        # Use the existing invoice creation logic
        invoice = self.env['account.move'].with_context(default_move_type="out_invoice").create_milestone_invoice([self.id])
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Milestone Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }


class SaleOrderPaymentMilestoneSub(models.Model):
    _name = 'sale.order.payment.milestone.sub'
    _description = 'Sale Order Payment Sub-milestone'
    _order = 'parent_milestone_id, sequence, id'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    
    parent_milestone_id = fields.Many2one(
        'sale.order.payment.milestone',
        string='Parent Milestone',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='Sub-milestone Name',
        required=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    percentage = fields.Float(
        string='Percentage (%)',
        digits=(5, 2),
        help='Percentage of parent milestone amount'
    )
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        compute='_compute_amount',
        store=True
    )
    currency_id = fields.Many2one(
        related='parent_milestone_id.currency_id',
        string='Currency'
    )
    
    # Date configuration
    date_type = fields.Selection([
        ('fixed', 'Fixed Date'),
        ('relative', 'Relative to Parent'),
        ('range', 'Date Range')
    ], string='Date Type', default='relative')
    
    planned_date = fields.Date(
        string='Planned Date'
    )
    actual_date = fields.Date(
        string='Actual Date'
    )
    fixed_date = fields.Date(
        string='Fixed Date'
    )
    days_offset = fields.Integer(
        string='Days Offset',
        default=0
    )
    date_range_start = fields.Date(
        string='Date Range Start'
    )
    date_range_end = fields.Date(
        string='Date Range End'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    
    description = fields.Html(
        string='Description'
    )
    required_documents = fields.Text(
        string='Required Documents'
    )
    
    # Delivery tracking
    delivery_phase = fields.Char(
        string='Delivery Phase'
    )
    expected_quantity = fields.Float(
        string='Expected Quantity'
    )
    quantity_uom = fields.Char(
        string='Unit of Measure'
    )
    
    # Invoice tracking
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice'
    )
    
    # Analytic tracking
    analytic_account_id = fields.Many2one(
        related='parent_milestone_id.analytic_account_id',
        string='Analytic Account',
        store=True,
        help='Analytic account from parent milestone'
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    
    @api.depends('percentage', 'parent_milestone_id.amount')
    def _compute_amount(self):
        """Compute sub-milestone amount"""
        for sub_milestone in self:
            if sub_milestone.parent_milestone_id and sub_milestone.percentage:
                sub_milestone.amount = sub_milestone.parent_milestone_id.amount * (sub_milestone.percentage / 100.0)
            else:
                sub_milestone.amount = 0.0
    
    # -------------------------------------------------------------------------
    # CONSTRAINS METHODS
    # -------------------------------------------------------------------------
    
    @api.constrains('percentage')
    def _check_percentage_range(self):
        """Validate percentage is within valid range"""
        for sub_milestone in self:
            if sub_milestone.percentage < 0 or sub_milestone.percentage > 100:
                raise ValidationError(_(
                    'Sub-milestone percentage must be between 0 and 100. '
                    'Current value: %.2f%%'
                ) % sub_milestone.percentage)
    
    @api.constrains('parent_milestone_id', 'percentage')
    def _check_total_percentage(self):
        """Validate that total sub-milestone percentages don't exceed 100%"""
        for sub_milestone in self:
            if sub_milestone.parent_milestone_id:
                total_percentage = sum(
                    sub_milestone.parent_milestone_id.sub_milestone_ids.mapped('percentage')
                )
                if total_percentage > 100:
                    raise ValidationError(_(
                        'Total sub-milestone percentages (%.2f%%) cannot exceed 100%% '
                        'for milestone "%s"'
                    ) % (total_percentage, sub_milestone.parent_milestone_id.milestone_name))
    
    @api.constrains('date_range_start', 'date_range_end')
    def _check_date_range(self):
        """Validate date range is logical"""
        for sub_milestone in self:
            if (sub_milestone.date_type == 'range' and 
                sub_milestone.date_range_start and 
                sub_milestone.date_range_end):
                if sub_milestone.date_range_start > sub_milestone.date_range_end:
                    raise ValidationError(_(
                        'Date range start cannot be after date range end for sub-milestone "%s"'
                    ) % sub_milestone.name)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    
    def action_set_ready(self):
        """Mark sub-milestone as ready"""
        self.write({'state': 'ready'})
        # Update parent progress
        self.parent_milestone_id._compute_progress_percentage()
        return True
    
    def action_complete(self):
        """Mark sub-milestone as completed"""
        self.write({
            'state': 'completed',
            'actual_date': fields.Date.today()
        })
        
        # Check if all sub-milestones are completed
        parent = self.parent_milestone_id
        all_completed = all(sub.state == 'completed' for sub in parent.sub_milestone_ids)
        if all_completed and parent.state == 'draft':
            parent.action_set_ready()
        
        # Update parent progress
        parent._compute_progress_percentage()
        
        return True
    
    def action_cancel(self):
        """Cancel sub-milestone"""
        self.write({'state': 'cancelled'})
        return True
    
    def action_reset_to_draft(self):
        """Reset sub-milestone to draft state and handle invoice"""
        self.ensure_one()
        
        # Restore sale order lines for this sub-milestone
        self._restore_sub_milestone_sale_lines()
        
        # Check if parent milestone has an invoice that might be related to this sub-milestone
        if self.parent_milestone_id.invoice_id:
            parent_invoice = self.parent_milestone_id.invoice_id
            
            # Find invoice lines that match this sub-milestone
            related_lines = parent_invoice.line_ids.filtered(
                lambda l: self.name in l.name and l.milestone_id == self.parent_milestone_id
            )
            
            if related_lines:
                if parent_invoice.state == 'draft':
                    # If invoice is draft, remove related lines
                    related_lines.unlink()
                    # If no lines left, unlink the entire invoice
                    if not parent_invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'income'):
                        parent_invoice.unlink()
                        self.parent_milestone_id.write({'invoice_id': False})
                elif parent_invoice.state == 'posted':
                    # Handle payments if invoice is paid
                    if parent_invoice.payment_state in ('paid', 'in_payment', 'partial'):
                        self._remove_sub_milestone_payments(parent_invoice)
                    
                    # Cancel and reset invoice to draft
                    parent_invoice.button_cancel()
                    parent_invoice.button_draft()
        
        # Reset sub-milestone to draft
        self.write({
            'state': 'draft',
            'actual_date': False
        })
        
        # Check if parent milestone status should be updated
        self._check_parent_milestone_status()
        return True
    
    def _remove_sub_milestone_payments(self, invoice):
        """Remove payments linked to invoice when resetting sub-milestone"""
        if not invoice or invoice.state != 'posted':
            return
        
        # Find payment moves linked to this invoice
        payment_moves = self.env['account.move'].search([
            ('line_ids.matched_debit_ids.debit_move_id', 'in', invoice.line_ids.ids),
            ('move_type', 'in', ['entry', 'in_receipt', 'out_receipt']),
            ('state', '=', 'posted')
        ])
        
        payment_moves |= self.env['account.move'].search([
            ('line_ids.matched_credit_ids.credit_move_id', 'in', invoice.line_ids.ids),
            ('move_type', 'in', ['entry', 'in_receipt', 'out_receipt']),
            ('state', '=', 'posted')
        ])
        
        # Remove reconciliation first
        for line in invoice.line_ids.filtered(lambda l: l.account_id.reconcile):
            if line.matched_debit_ids or line.matched_credit_ids:
                line.remove_move_reconcile()
        
        # Cancel and unlink payment moves
        for payment_move in payment_moves:
            if payment_move.state == 'posted':
                payment_move.button_cancel()
            payment_move.unlink()
    
    def _restore_sub_milestone_sale_lines(self):
        """Restore sale order line amounts when resetting sub-milestone"""
        sale_order = self.parent_milestone_id.sale_order_id
        if not sale_order:
            return
        
        # Find sub-milestone specific sale order lines
        sub_milestone_lines = sale_order.order_line.filtered(
            lambda l: l.sequence >= 9999 and self.name in l.name
        )
        
        # Calculate amount to restore
        restore_amount = sum(sub_milestone_lines.mapped(lambda l: l.price_unit * l.product_uom_qty))
        
        # Set sub-milestone lines quantity to zero (can't unlink in confirmed orders)
        sub_milestone_lines.write({'product_uom_qty': 0})
        
        # Restore original lines proportionally
        if restore_amount > 0:
            original_lines = sale_order.order_line.filtered(lambda l: l.sequence < 9999)
            if original_lines:
                current_total = sum(original_lines.mapped(lambda l: l.price_unit * l.product_uom_qty))
                
                for line in original_lines:
                    current_line_total = line.price_unit * line.product_uom_qty
                    if current_total > 0:
                        line_proportion = current_line_total / current_total
                        additional_amount = restore_amount * line_proportion
                        new_line_total = current_line_total + additional_amount
                        new_price_unit = new_line_total / line.product_uom_qty if line.product_uom_qty else 0
                        line.write({'price_unit': new_price_unit})
    
    def action_create_invoice(self):
        """Create invoice for this sub-milestone"""
        self.ensure_one()
        if self.state != 'completed':
            raise ValidationError(_('Only completed sub-milestones can be invoiced'))
        
        # Create a temporary milestone record for invoice creation
        temp_milestone_vals = {
            'sale_order_id': self.parent_milestone_id.sale_order_id.id,
            'milestone_name': f"{self.parent_milestone_id.milestone_name} - {self.name}",
            'percentage': self.percentage,
            'amount': self.amount,
            'state': 'ready',
            'sequence': self.sequence,
        }
        temp_milestone = self.env['sale.order.payment.milestone'].create(temp_milestone_vals)
        
        try:
            # Create invoice using the temp milestone with analytic distribution
            invoice = self.env['account.move'].with_context(default_move_type="out_invoice").create_milestone_invoice([temp_milestone.id])
            
            # Ensure invoice lines have analytic distribution from parent milestone
            if self.analytic_account_id:
                income_lines = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'income')
                for line in income_lines:
                    if not line.analytic_distribution:
                        line.analytic_distribution = {self.analytic_account_id.id: 100}
            
            # Link the invoice to the parent milestone instead
            self.parent_milestone_id.write({'invoice_id': invoice.id})
            
            # Mark sub-milestone as invoiced
            self.write({'state': 'invoiced'})
            
            # Check if all sub-milestones are invoiced and update parent
            self._check_parent_milestone_status()
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Sub-milestone Invoice'),
                'res_model': 'account.move',
                'res_id': invoice.id,
                'view_mode': 'form',
                'target': 'current',
            }
        finally:
            # Clean up temp milestone
            temp_milestone.unlink()
    
    def _check_parent_milestone_status(self):
        """Check if parent milestone should be updated based on sub-milestone states"""
        parent = self.parent_milestone_id
        if not parent.sub_milestone_ids:
            return
        
        # Check if all sub-milestones are invoiced
        all_invoiced = all(sub.state == 'invoiced' for sub in parent.sub_milestone_ids)
        if all_invoiced and parent.state != 'invoiced':
            parent.write({'state': 'invoiced'})
        elif not all_invoiced and parent.state == 'invoiced':
            # If not all sub-milestones are invoiced but parent is, reset parent to ready
            parent.write({'state': 'ready'})
        
        # Trigger progress percentage recalculation
        parent._compute_progress_percentage()