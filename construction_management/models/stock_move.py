# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ConstructionStockMove(models.Model):
    _inherit = 'stock.move'

    construction_project_id = fields.Many2one('project.project', 'Construction Project', domain="[('is_construction', '=', True)]")
    boq_task_id = fields.Many2one('project.task', 'BOQ Item', domain="[('project_id', '=', 'construction_project_id')]")
    cost_code_id = fields.Many2one('construction.cost.code', 'Cost Code')

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        res = super(ConstructionStockMove, self)._create_account_move_line(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        if self.construction_project_id:
            for line in res:
                line.analytic_distribution = {self.construction_project_id.analytic_account_id.id: 100}
        return res

    def _action_done(self, cancel_backorder=False):
        res = super(ConstructionStockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in self.filtered(lambda m: m.boq_task_id and m.state == 'done'):
            # Update actual quantity on the BOQ item
            move.boq_task_id.actual_quantity += move.quantity_done

            # The actual cost will be updated by the account move lines
            # that are created from the stock move, so we don't need to do anything here
            # for the actual cost.

        return res
