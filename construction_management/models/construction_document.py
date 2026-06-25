# -*- coding: utf-8 -*-

from odoo import models, fields, api

# Document directory model is defined in construction_document_directory.py


# Submittal model is defined in construction_submittal.py


class ConstructionQualityInspection(models.Model):
    _name = 'construction.quality.inspection'
    _description = 'Construction Quality Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char('Inspection Name', required=True)
    project_id = fields.Many2one('project.project', 'Project', required=True)
    inspection_type = fields.Selection([
        ('concrete_strength', 'Concrete Strength'),
        ('reinforcement', 'Reinforcement'),
        ('masonry', 'Masonry'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('other', 'Other')
    ], string='Type', required=True)
    task_id = fields.Many2one('project.task', 'Related Task')
    inspector_id = fields.Many2one('res.partner', 'Inspector')
    inspection_date = fields.Date('Inspection Date')
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('pending', 'Pending')
    ], string='Status', default='scheduled', tracking=True)
    notes = fields.Text('Notes')
    
    def action_start_inspection(self):
        self.state = 'in_progress'
    
    def action_pass_inspection(self):
        self.state = 'passed'
    
    def action_fail_inspection(self):
        self.state = 'failed'
    
    def action_reset_to_scheduled(self):
        self.state = 'scheduled'


class ConstructionIncident(models.Model):
    _name = 'construction.incident'
    _description = 'Construction Safety Incident'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char('Incident Title', required=True)
    project_id = fields.Many2one('project.project', 'Project', required=True)
    incident_type = fields.Selection([
        ('injury', 'Injury'),
        ('near_miss', 'Near Miss'),
        ('property_damage', 'Property Damage'),
        ('environmental', 'Environmental'),
        ('other', 'Other')
    ], string='Type', required=True)
    severity = fields.Selection([
        ('low', 'Low'),
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical')
    ], string='Severity', required=True)
    incident_date = fields.Datetime('Incident Date', required=True)
    location = fields.Char('Location')
    description = fields.Text('Description', required=True)
    reported_by_id = fields.Many2one('res.users', 'Reported By')
    state = fields.Selection([
        ('reported', 'Reported'),
        ('under_investigation', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ], string='Status', default='reported', tracking=True)
    resolution_date = fields.Date('Resolution Date')
    corrective_action = fields.Text('Corrective Action')
    
    def action_start_investigation(self):
        self.state = 'under_investigation'
    
    def action_resolve_incident(self):
        self.state = 'resolved'
        self.resolution_date = fields.Date.today()
    
    def action_close_incident(self):
        self.state = 'closed'
    
    def action_reopen_incident(self):
        self.state = 'reported'
        self.resolution_date = False