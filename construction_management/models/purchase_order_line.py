# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ConstructionPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    construction_project_id = fields.Many2one('project.project', 'Construction Project', domain="[('is_construction', '=', True)]")
    boq_task_id = fields.Many2one('project.task', 'BOQ Item', domain="[('project_id', '=', 'construction_project_id')]")
    cost_code_id = fields.Many2one('construction.cost.code', 'Cost Code')
    price_variance = fields.Monetary('Price Variance', compute='_compute_price_variance', store=True, readonly=True)

    @api.depends('price_unit', 'boq_task_id.unit_cost')
    def _compute_price_variance(self):
        for line in self:
            if line.boq_task_id:
                line.price_variance = line.price_unit - line.boq_task_id.unit_cost
            else:
                line.price_variance = 0.0

    @api.onchange('construction_project_id')
    def _onchange_construction_project(self):
        if self.construction_project_id:
            self.analytic_distribution = {self.construction_project_id.analytic_account_id.id: 100}
        else:
            self.analytic_distribution = {}
