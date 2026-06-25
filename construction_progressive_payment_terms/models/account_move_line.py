# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    
    # Progressive payment milestone tracking
    milestone_id = fields.Many2one(
        'sale.order.payment.milestone',
        string='Payment Milestone',
        help='Related payment milestone for progressive payments'
    )
    milestone_type = fields.Selection(
        related='milestone_id.milestone_type',
        string='Milestone Type',
        store=True,
        help='Type of milestone'
    )
    milestone_name = fields.Char(
        string='Milestone Name',
        help='Name of the milestone for display purposes'
    )
    is_milestone_line = fields.Boolean(
        string='Is Milestone Line',
        compute='_compute_is_milestone_line',
        store=True,
        help='Whether this line is related to a milestone'
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    
    @api.depends('milestone_id')
    def _compute_is_milestone_line(self):
        """Compute if this line is related to a milestone"""
        for line in self:
            line.is_milestone_line = bool(line.milestone_id)

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------
    
    def _compute_name(self):
        """Override to include milestone information in payment term lines"""
        result = super()._compute_name()
        
        for line in self:
            # Only modify name for milestone-related lines
            if (line.milestone_id and 
                line.account_id.user_type_id.type in ('receivable', 'payable')):
                
                milestone_info = f" - {line.milestone_id.milestone_name}"
                if line.milestone_id.percentage:
                    milestone_info += f" ({line.milestone_id.percentage}%)"
                
                # Append milestone info to existing name
                if line.name:
                    line.name = line.name + milestone_info
                else:
                    line.name = line.milestone_id.milestone_name
        
        return result

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    
    def update_milestone_reference(self, milestone_id):
        """Update milestone reference for this line"""
        self.ensure_one()
        milestone = self.env['sale.order.payment.milestone'].browse(milestone_id)
        
        self.write({
            'milestone_id': milestone_id,
            'milestone_name': milestone.milestone_name,
        })
        
        # Recompute name to include milestone information
        self._compute_name()
        
        return True