# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ConstructionSubmittal(models.Model):
    _name = 'construction.submittal'
    _description = 'Construction Submittal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char('Submittal Number', required=True, tracking=True)
    project_id = fields.Many2one('project.project', 'Project', required=True, domain="[('is_construction', '=', True)]", tracking=True)
    task_id = fields.Many2one('project.task', 'Related Task', domain="[('project_id', '=', 'project_id')]")
    subcontractor_id = fields.Many2one('construction.subcontractor', 'Subcontractor', tracking=True)
    
    description = fields.Text('Description')
    submittal_type = fields.Selection([
        ('shop_drawings', 'Shop Drawings'),
        ('product_data', 'Product Data'),
        ('samples', 'Samples'),
        ('certificates', 'Certificates'),
        ('test_reports', 'Test Reports'),
        ('other', 'Other'),
    ], string='Submittal Type', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('resubmit', 'Resubmit Required')
    ], string='Status', default='draft', tracking=True)

    submission_date = fields.Date('Submission Date', default=fields.Date.today())
    required_date = fields.Date('Required Date')
    review_deadline = fields.Date('Review Deadline')
    approval_date = fields.Date('Approval Date')

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    attachment_count = fields.Integer('Attachment Count', compute='_compute_attachment_count')
    review_comments = fields.Text('Review Comments')
    reviewer_id = fields.Many2one('res.users', 'Reviewer')

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for submittal in self:
            submittal.attachment_count = len(submittal.attachment_ids)

    def action_submit(self):
        self.write({'state': 'submitted'})
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=f'Submittal Review Required: {self.name}',
            note=f'Submittal {self.name} has been submitted for review.',
            user_id=self.reviewer_id.id or self.env.user.id
        )

    def action_send_for_review(self):
        self.write({'state': 'under_review'})

    def action_approve(self):
        self.write({'state': 'approved', 'approval_date': fields.Date.today()})
        self.activity_feedback([
            'mail.mail_activity_data_todo',
        ])
        self.message_post(body=f"Submittal {self.name} has been approved.")

    def action_reject(self):
        self.write({'state': 'rejected'})
        self.activity_feedback([
            'mail.mail_activity_data_todo',
        ])
        self.message_post(body=f"Submittal {self.name} has been rejected.")

    def action_resubmit(self):
        self.write({'state': 'resubmit'})

    def action_view_attachments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attachments'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {'default_res_id': self.id, 'default_res_model': 'construction.submittal'},
        }
