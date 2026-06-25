from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_pdc_journal = fields.Boolean(string="Is PDC Journal", help="Indicates if the journal is used for Post Dated Cheques.")
    is_salary_journal = fields.Boolean(string="Is Salary Journal", help="Indicates if the journal is used for Salary Payments.")