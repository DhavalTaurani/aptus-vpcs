from odoo import models, api, _, fields
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        for vals in vals_list:
            company = self.env['res.company'].browse(vals.get('company_id')) if vals.get('company_id') else self.env.company

            if not vals.get('name') or vals['name'] in ['New', '/']:
                if company.name == 'SOFTWARE':
                    seq_code = 'purchase.order.software'
                elif company.name == 'INFRA':
                    seq_code = 'purchase.order.elv'
                elif company.name == 'SOLAR':
                    seq_code = 'purchase.order.solar'
                elif company.name == 'Smart Grid Innovations LLC':
                    seq_code = 'purchase.order.sgi'
                else:
                    # continue
                    raise UserError("❌ Purchase Order sequence not configured for this company.")

                new_name = self.env['ir.sequence'].next_by_code(seq_code)

                if not new_name:
                    raise UserError(f"❌ Sequence code '{seq_code}' not found or not configured.")

                # Check for duplicates (optional in batch mode)
                existing = self.search([
                    ('name', '=', new_name),
                    ('company_id', '=', company.id)
                ], limit=1)

                if existing:
                    raise UserError(
                        _("❌ The generated RFQ/PO number '%s' already exists in company '%s'. Check the sequence configuration.") % (
                            new_name, company.name))

                vals['name'] = new_name

        return super(PurchaseOrder, self).create(vals_list)
