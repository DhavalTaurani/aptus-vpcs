# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPaymentTermLineSubTemplate(models.Model):
    _name = 'account.payment.term.line.sub.template'
    _description = 'Payment Term Sub-milestone Template'
    _order = 'payment_term_line_id, sequence, id'

    payment_term_line_id = fields.Many2one(
        'account.payment.term.line',
        string='Payment Term Line',
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
    
    description = fields.Text(
        string='Description'
    )
    
    @api.constrains('percentage')
    def _check_percentage_range(self):
        """Validate percentage is within valid range"""
        for template in self:
            if template.percentage < 0 or template.percentage > 100:
                raise ValidationError(_('Sub-milestone percentage must be between 0 and 100'))
    
    @api.constrains('payment_term_line_id', 'percentage')
    def _check_total_percentage(self):
        """Validate that total sub-milestone percentages don't exceed 100%"""
        for template in self:
            if template.payment_term_line_id:
                total_percentage = sum(
                    template.payment_term_line_id.sub_milestone_template_ids.mapped('percentage')
                )
                if total_percentage > 100:
                    raise ValidationError(_('Total sub-milestone percentages cannot exceed 100%%'))