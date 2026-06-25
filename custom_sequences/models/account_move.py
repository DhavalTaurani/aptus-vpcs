from odoo import models, _, fields ,api
from odoo.exceptions import UserError
from datetime import date

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_default_journal(self):
        """Default journal based on move_type and company."""
        move_type = self._context.get("default_move_type")
        company = self.env.company

        if move_type == "entry":
            # Manual Journal Entries → Journal Voucher (Miscellaneous)
            journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('name', 'ilike', 'Journal Voucher'),
                ('company_id', '=', company.id),
            ], limit=1)
            if journal:
                return journal

        elif move_type == "out_invoice":
            # Customer Invoices → Sale Journal
            journal = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', company.id),
            ], limit=1)
            if journal:
                return journal

        elif move_type == "in_invoice":
            # Vendor Bills → Purchase Journal
            journal = self.env['account.journal'].search([
                ('type', '=', 'purchase'),
                ('company_id', '=', company.id),
            ], limit=1)
            if journal:
                return journal

        return None


    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        default=_get_default_journal,
        domain="[('company_id', '=', company_id)]",
    )


    def action_post(self):
        if self.date and self.date < date(2026, 1, 1):
            return super(AccountMove, self).action_post()
        
        # Define sequence mapping per type and company
        sequence_map = {
            'out_invoice': {
                'SOFTWARE': 'invoice.software',
                'INFRA': 'invoice.elv',
                'SOLAR': 'invoice.solar',
                'Smart Grid Innovations LLC': 'invoice.sgi',
            },
            'in_invoice': {
                'SOFTWARE': 'bill.software',
                'INFRA': 'bill.elv',
                'SOLAR': 'bill.solar',
                'Smart Grid Innovations LLC': 'bill.sgi',
            },
            'entry': {
                'SOFTWARE': 'JOURNAL - SOFTWARE',
                'INFRA': 'JOURNAL - ELV',
                'SOLAR': 'JOURNAL - SOLAR',
                'Oriental Oryx International LLC': 'JOURNAL - Oriental Oryx',
                'Smart Grid Innovations LLC': 'JOURNAL - SGI',
            },
            # New mapping for Salary Journals
            'salary_special': {
                'SOFTWARE': 'JOURNAL - SALARY SOFTWARE',
                'INFRA': 'JOURNAL - SALARY ELV',
                'SOLAR': 'JOURNAL - SALARY SOLAR',
                'Oriental Oryx International LLC': 'JOURNAL - SALARY ORIENTAL',
                'Smart Grid Innovations LLC': 'JOURNAL - SALARY SGI',
            }
        }

        for move in self:
            # 1. Skip if already has a name
            if move.name and move.name not in ['/', 'Draft', False]:
                continue

            company_name = move.company_id.name

            # 2. Determine which sequence category to use
            if move.journal_id.is_salary_journal:
                # Direct to the salary sequences regardless of move_type
                sequence_code = sequence_map.get('salary_special', {}).get(company_name)
            else:
                # Standard logic for non-salary journals
                if move.move_type == 'in_invoice' and not move.invoice_date:
                    raise UserError(_("The Bill/Refund date is required to validate this document."))
                sequence_code = sequence_map.get(move.move_type, {}).get(company_name)
            # 3. Validation and Generation
            if not sequence_code:
                # continue
                raise UserError(_("No sequence defined for company '%s' and journal/type configuration.")
                                % (company_name))

            new_name = self.env['ir.sequence'].next_by_code(sequence_code)

            if not new_name:
                raise UserError(_("Sequence '%s' not configured or returned no value.") % sequence_code)

            # 4. Uniqueness check
            existing = self.search([
                ('name', '=', new_name),
                ('company_id', '=', move.company_id.id),
                ('id', '!=', move.id)
            ], limit=1)
            if existing:
                raise UserError(_("The generated number '%s' already exists.") % new_name)

            move.name = new_name
        return super(AccountMove, self).action_post()



class AccountJournal(models.Model):
    _inherit = "account.journal"

    code = fields.Char(string="Short Code", size=20, required=True)
