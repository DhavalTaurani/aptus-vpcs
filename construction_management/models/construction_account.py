# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    subcontractor_id = fields.Many2one(
        'construction.subcontractor',
        string='Subcontractor',
        index=True,
        tracking=True,
    )