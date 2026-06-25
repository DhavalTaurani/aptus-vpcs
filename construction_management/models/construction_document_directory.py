# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ConstructionDocumentDirectory(models.Model):
    _name = 'construction.document.directory'
    _description = 'Construction Document Directory'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char('Directory Name', required=True, tracking=True)
    # project_id = fields.Many2one('project.project', 'Project', required=True, domain="[('is_construction', '=', True)]", tracking=True)
    parent_id = fields.Many2one('construction.document.directory', 'Parent Directory', ondelete='cascade')
    child_ids = fields.One2many('construction.document.directory', 'parent_id', 'Subdirectories')

    document_type = fields.Selection([
        ('drawings', 'Drawings'),
        ('specifications', 'Specifications'),
        ('contracts', 'Contracts'),
        ('permits', 'Permits'),
        ('submittals', 'Submittals'),
        ('transmittals', 'Transmittals'),
        ('reports', 'Reports'),
        ('photos', 'Photos'),
        ('correspondence', 'Correspondence'),
        ('other', 'Other'),
    ], string='Document Type', tracking=True)

    attachment_ids = fields.One2many('ir.attachment', 'res_id',
                                    domain=[('res_model', '=', 'construction.document.directory')],
                                    string='Documents')
    document_count = fields.Integer('Document Count', compute='_compute_document_count', store=True)
    subdirectory_count = fields.Integer('Subdirectory Count', compute='_compute_subdirectory_count', store=True)

    @api.depends('attachment_ids')
    def _compute_document_count(self):
        for directory in self:
            directory.document_count = len(directory.attachment_ids)

    @api.depends('child_ids')
    def _compute_subdirectory_count(self):
        for directory in self:
            directory.subdirectory_count = len(directory.child_ids)

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('res_id', '=', self.id), ('res_model', '=', 'construction.document.directory')],
            'context': {'default_res_id': self.id, 'default_res_model': 'construction.document.directory'},
        }

    def action_view_subdirectories(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subdirectories'),
            'res_model': 'construction.document.directory',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id, 'default_project_id': self.project_id.id},
        }
