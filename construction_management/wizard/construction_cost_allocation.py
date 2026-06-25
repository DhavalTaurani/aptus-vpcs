# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ConstructionCostAllocation(models.TransientModel):
    _name = 'construction.cost.allocation'
    _description = 'Cost Allocation Wizard'

    @api.model
    def default_get(self, fields_list):
        res = super(ConstructionCostAllocation, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'account.move' and self.env.context.get('active_id'):
            move = self.env['account.move'].browse(self.env.context.get('active_id'))
            if move.move_type != 'in_invoice' or move.state != 'posted':
                raise UserError(_("Cost allocation can only be done from a posted vendor bill."))
            res['move_id'] = move.id
            res['total_to_allocate'] = move.amount_untaxed
            # Try to find a project from the analytic account on the bill
            if move.invoice_line_ids:
                analytic_accounts = move.invoice_line_ids.mapped('analytic_distribution')
                if analytic_accounts:
                    # This is a simplification; you might need more complex logic
                    # if multiple analytic accounts point to different projects.
                    analytic_account_id = list(analytic_accounts.keys())[0]
                    project = self.env['project.project'].search([('analytic_account_id', '=', int(analytic_account_id))], limit=1)
                    if project:
                        res['project_id'] = project.id
        return res

    move_id = fields.Many2one('account.move', string="Vendor Bill", required=True, readonly=True)
    project_id = fields.Many2one('project.project', string="Construction Project", required=True, domain="[('is_construction', '=', True)]")
    allocation_line_ids = fields.One2many('construction.cost.allocation.line', 'wizard_id', string="Allocation Lines")
    
    total_to_allocate = fields.Monetary(string="Total to Allocate", readonly=True, currency_field='currency_id')
    total_allocated = fields.Monetary(string="Total Allocated", compute='_compute_totals', currency_field='currency_id')
    remaining_amount = fields.Monetary(string="Remaining", compute='_compute_totals', currency_field='currency_id')
    currency_id = fields.Many2one(related='move_id.currency_id')

    @api.depends('allocation_line_ids.amount')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_allocated = sum(wizard.allocation_line_ids.mapped('amount'))
            wizard.remaining_amount = wizard.total_to_allocate - wizard.total_allocated

    def allocate_costs(self):
        self.ensure_one()
        if not self.allocation_line_ids:
            raise UserError(_("You must specify at least one allocation line."))
        
        if abs(self.total_to_allocate - self.total_allocated) > self.currency_id.rounding:
            raise UserError(_("The total allocated amount must equal the bill's untaxed total."))

        analytic_line_obj = self.env['account.analytic.line']
        for line in self.allocation_line_ids:
            if line.amount <= 0:
                continue
            
            analytic_line_obj.create({
                'name': f"{self.move_id.name}: {line.task_id.name}",
                'account_id': self.project_id.analytic_account_id.id,
                'task_id': line.task_id.id,
                'amount': -line.amount,  # Costs are negative in analytic accounting
                'ref': self.move_id.name,
                'date': self.move_id.date,
                'partner_id': self.move_id.partner_id.id,
                'move_line_id': self.move_id.invoice_line_ids[0].id, # Simplification
            })
        
        self.move_id.message_post(body=_("Costs from this bill have been allocated to BOQ items."))
        return {'type': 'ir.actions.act_window_close'}

class ConstructionCostAllocationLine(models.TransientModel):
    _name = 'construction.cost.allocation.line'
    _description = 'Cost Allocation Wizard Line'

    wizard_id = fields.Many2one('construction.cost.allocation', string="Wizard", required=True, ondelete='cascade')
    task_id = fields.Many2one(
        'project.task',
        string="BOQ Item",
        required=True,
        domain="[('project_id', '=', parent.project_id), ('is_boq_item', '=', True)]"
    )
    amount = fields.Monetary(string="Amount to Allocate", required=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id')
