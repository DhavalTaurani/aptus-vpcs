from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    quotation_name = fields.Char(string="Quotation Number", readonly=True)

    @api.model
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        for vals in vals_list:
            company = self.env['res.company'].browse(vals.get('company_id')) if vals.get(
                'company_id') else self.env.company

            if vals.get('name', '/') in ['/', 'New', False]:
                if company.name == 'SOFTWARE':
                    seq_code = 'sale.order.software.quotation'
                elif company.name == 'INFRA':
                    seq_code = 'sale.order.elv.quotation'
                elif company.name == 'SOLAR':
                    seq_code = 'sale.order.solar.quotation'
                elif company.name == 'Smart Grid Innovations LLC':
                    seq_code = 'sale.order.sgi.quotation'
                else:
                    # continue
                    raise UserError("❌ Sequence not configured for this company. Please check multi-company setup.")

                new_name = self.env['ir.sequence'].next_by_code(seq_code)
                
                if not new_name:
                    raise UserError(
                        f"❌ Sequence code '{seq_code}' not found. Please configure it in technical settings.")

                existing = self.search([
                    ('name', '=', new_name),
                    ('company_id', '=', company.id)
                ], limit=1)

                if existing:
                    raise UserError(
                        _("❌ The generated Quotation number '%s' already exists for company '%s'. Please review the sequence.") % (
                            new_name, company.name))

                vals['name'] = new_name

        return super(SaleOrder, self).create(vals_list)

    def action_confirm(self):
        for order in self:
            if order.name.startswith(("QT/","AI/")):
                order.quotation_name = order.name

                company = order.company_id
                if company.name == 'SOFTWARE':
                    seq_code = 'sale.order.software'
                elif company.name == 'INFRA':
                    seq_code = 'sale.order.elv'
                elif company.name == 'SOLAR':
                    seq_code = 'sale.order.solar'
                elif company.name == 'Smart Grid Innovations LLC':
                    seq_code = 'sale.order.sgi'
                else:
                    raise UserError("❌ Sales Order sequence not configured for this company.")

                new_name = self.env['ir.sequence'].next_by_code(seq_code)
                
                if not new_name:
                    raise UserError(f"❌ Sequence code '{seq_code}' not found.")

                # ✅ Check for duplicates
                existing = self.search([
                    ('name', '=', new_name),
                    ('company_id', '=', company.id),
                    ('id', '!=', order.id)
                ], limit=1)

                if existing:
                    raise UserError(
                        _("❌ The generated Sales Order number '%s' already exists for company '%s'. Please check the sequence settings.") % (
                            new_name, company.name))

                order.name = new_name

        return super(SaleOrder, self).action_confirm()