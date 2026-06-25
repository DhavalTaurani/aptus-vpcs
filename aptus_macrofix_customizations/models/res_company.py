from odoo import api, fields, models

class Company(models.Model):
    _inherit = 'res.company'

    oriental_oryx_stamp = fields.Binary("Main Stamp", attachment=True)
    aptus_stamp = fields.Binary("Aptus Stamp", attachment=True)