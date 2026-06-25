# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ConstructionAssignSubcontractor(models.TransientModel):
    _name = 'construction.assign.subcontractor'
    _description = 'Assign Subcontractor to Tasks Wizard'
    
    subcontractor_id = fields.Many2one('construction.subcontractor', 'Subcontractor', required=True)
    task_ids = fields.Many2many('project.task', string='Tasks to Assign')
    
    def assign_subcontractor(self):
        """Assign subcontractor to selected tasks"""
        for task in self.task_ids:
            task.write({'subcontractor_id': self.subcontractor_id.id})
        
        # Also update the subcontractor's task list
        self.subcontractor_id.write({
            'task_ids': [(4, task.id) for task in self.task_ids]
        })
        
        return {'type': 'ir.actions.act_window_close'}