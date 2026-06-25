from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    # removing 'P' from the payment sequences.
    def _get_starting_sequence(self):
        self.ensure_one()

        if self.journal_id.type in ['sale', 'bank', 'cash']:
            starting_sequence = "%s/%04d/00000" % (self.journal_id.code, self.date.year)
        else:
            starting_sequence = "%s/%04d/%02d/0000" % (self.journal_id.code, self.date.year, self.date.month)

        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence

        # REMOVE this part that adds 'P' before payments:
        # if self.journal_id.payment_sequence and self.payment_id:
        #     starting_sequence = "P" + starting_sequence

        return starting_sequence

    # /removing 'P' from the payment sequences.

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    inst_type = fields.Selection(
        selection=[
            ('chq', 'Cheque'),
            ('transfer', 'Transfer'),
            ('others', 'Others'),
            ('not_applicable', 'N/A'),
        ],
        string='Instrument Type'
    )

    inst_no = fields.Char('Instrument No')
