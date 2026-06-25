# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ConstructionBoqImport(models.TransientModel):
    _name = 'construction.boq.import'
    _description = 'BOQ Import Wizard'
    
    # Placeholder - will be implemented in task 14.2
    name = fields.Char('Name', required=True)