from odoo import api, models, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        res = super(AccountPayment, self).action_post()

        for payment in self:
            company = payment.company_id
            sequence_code = None

            if payment.payment_type == 'inbound' and not payment.journal_id.is_pdc_journal:
                if company.name == 'SOFTWARE':
                    sequence_code = 'Receipt - SOFTWARE'
                elif company.name == 'INFRA':
                    sequence_code = 'Receipt - ELV'
                elif company.name == 'SOLAR':
                    sequence_code = 'Receipt - SOLAR'
                elif company.name == 'Smart Grid Innovations LLC':
                    sequence_code = 'Receipt - SGI'

            elif payment.payment_type == 'inbound' and payment.journal_id.is_pdc_journal:
                if company.name == 'SOFTWARE':
                    sequence_code = 'RECEIPT - PDC SOFTWARE'
                elif company.name == 'INFRA':
                    sequence_code = 'RECEIPT - PDC ELV'
                elif company.name == 'SOLAR':
                    sequence_code = 'RECEIPT - PDC SOLAR'
                elif company.name == 'Smart Grid Innovations LLC':
                    sequence_code = 'RECEIPT - PDC SGI'


            elif payment.payment_type == 'outbound' and not payment.journal_id.is_pdc_journal:
                if company.name == 'SOFTWARE':
                    sequence_code = 'PAYMENT - SOFTWARE'
                elif company.name == 'INFRA':
                    sequence_code = 'PAYMENT - ELV'
                elif company.name == 'SOLAR':
                    sequence_code = 'PAYMENT - SOLAR'
                elif company.name == 'Oriental Oryx International LLC':
                    sequence_code = 'SALARY - ORIENTAL'
                elif company.name == 'Smart Grid Innovations LLC':
                    sequence_code = 'PAYMENT - SGI'

                
            elif payment.payment_type == 'outbound' and payment.journal_id.is_pdc_journal:
                if company.name == 'SOFTWARE':
                    sequence_code = 'PAYMENT - PDC SOFTWARE'
                elif company.name == 'INFRA':
                    sequence_code = 'PAYMENT - PDC ELV'
                elif company.name == 'SOLAR':
                    sequence_code = 'PAYMENT - PDC SOLAR'
                elif company.name == 'Smart Grid Innovations LLC':
                    sequence_code = 'PAYMENT - PDC SGI'

            if not sequence_code:
                raise UserError(_("Missing sequence code for this payment."))

            sequence = self.env['ir.sequence'].with_company(company.id).search([
                ('code', '=', sequence_code),
                ('company_id', '=', company.id)
            ], limit=1)
            if not sequence:
                raise UserError(_("Sequence '%s' not found for %s.") % (sequence_code, company.name))

            if not (payment.name or '').startswith(('PYT', 'RCT')):
                new_name = sequence.next_by_id()
                payment.move_id.name = new_name
                payment.name = new_name

        return res