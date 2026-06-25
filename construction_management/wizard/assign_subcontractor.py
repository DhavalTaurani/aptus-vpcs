# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AssignSubcontractor(models.TransientModel):
    _name = 'construction.assign.subcontractor'
    _description = 'Assign Subcontractor to BOQ Items'

    subcontractor_id = fields.Many2one('construction.subcontractor', 'Subcontractor', required=True)
    task_ids = fields.Many2many('project.task', string='BOQ Items', domain="[('is_boq_item', '=', True)]")

    def assign_subcontractor(self):
        if not self.task_ids:
            raise UserError(_("Please select at least one BOQ item to assign."))
        
        for task in self.task_ids:
            task.write({'subcontractor_id': self.subcontractor_id.id})

        return {'type': 'ir.actions.act_window_close'}
