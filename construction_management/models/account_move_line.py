# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ConstructionAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Construction references
    construction_project_id = fields.Many2one('project.project', 'Construction Project', domain="[('is_construction', '=', True)]")
    boq_task_id = fields.Many2one('project.task', 'BOQ Item', domain="[('project_id', '=', 'construction_project_id')]")
    cost_code_id = fields.Many2one('construction.cost.code', 'Cost Code')

    # Retention handling
    retention_percentage = fields.Float('Retention %')
    retention_amount = fields.Monetary('Retention Amount', compute='_compute_retention_amount', store=True)
    is_retention_line = fields.Boolean('Is Retention Line')

    @api.depends('retention_percentage', 'price_subtotal')
    def _compute_retention_amount(self):
        for line in self:
            line.retention_amount = line.price_subtotal * (line.retention_percentage / 100)

    @api.onchange('construction_project_id')
    def _onchange_construction_project(self):
        if self.construction_project_id:
            self.analytic_distribution = {self.construction_project_id.analytic_account_id.id: 100}
        else:
            self.analytic_distribution = {}
