from odoo import models, api, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'

    project_sequence = fields.Char(string="Custom Sequence", copy=False)

    @api.model
    def create(self, vals_list):
        for vals in vals_list:
            seq = self.env['ir.sequence'].next_by_code('project.custom')
            if seq:
                vals['project_sequence'] = seq
                # if vals.get('name'):
                #     vals['name'] = f"{seq} - {vals['name']}"
                # else:
                #     vals['name'] = seq
        return super().create(vals_list)
