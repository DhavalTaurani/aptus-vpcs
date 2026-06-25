# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ConstructionProgressUpdate(models.TransientModel):
    _name = 'construction.progress.update'
    _description = 'Update Progress for BOQ Items'

    @api.model
    def default_get(self, fields_list):
        res = super(ConstructionProgressUpdate, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids and self.env.context.get('active_model') == 'project.task':
            tasks = self.env['project.task'].browse(active_ids)
            boq_tasks = tasks.filtered(lambda t: t.is_boq_item)
            if not boq_tasks:
                raise UserError(_("The selected records must be BOQ items to update progress."))
            res['task_ids'] = [(6, 0, boq_tasks.ids)]
        return res

    task_ids = fields.Many2many(
        'project.task',
        string='BOQ Items',
        required=True,
        readonly=True,
        help="These are the BOQ items for which the progress will be updated."
    )
    
    new_physical_progress = fields.Float(
        'New Physical Progress (%)',
        required=True,
        help="Set the new physical progress percentage for the selected items."
    )

    def update_progress(self):
        self.ensure_one()
        if not (0 <= self.new_physical_progress <= 100):
            raise UserError(_("Physical progress must be between 0 and 100 percent."))

        if not self.task_ids:
            raise UserError(_("Please select at least one BOQ Item to update."))

        self.task_ids.write({
            'physical_progress': self.new_physical_progress
        })

        return {'type': 'ir.actions.act_window_close'}
