from odoo import models, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        for vals in vals_list:
            company = self.env['res.company'].browse(vals.get('company_id')) if vals.get('company_id') else self.env.company
            picking_type_code = vals.get('picking_type_code') or 'internal'

            if vals.get('name', '/') in ['/', 'New', False]:
                seq_code = None

                if picking_type_code == 'outgoing':
                    if company.name == 'SOFTWARE':
                        seq_code = 'stock.picking.delivery.software'
                    elif company.name == 'INFRA':
                        seq_code = 'stock.picking.delivery.elv'
                    elif company.name == 'SOLAR':
                        seq_code = 'stock.picking.delivery.solar'
                    elif company.name == 'Smart Grid Innovations LLC':
                        seq_code = 'stock.picking.delivery.sgi'
                    else:
                        raise UserError("❌ Delivery Order sequence not configured for this company.")

                elif picking_type_code == 'incoming':
                    if company.name == 'SOFTWARE':
                        seq_code = 'stock.picking.grn.software'
                    elif company.name == 'INFRA':
                        seq_code = 'stock.picking.grn.elv'
                    elif company.name == 'SOLAR':
                        seq_code = 'stock.picking.grn.solar'
                    elif company.name == 'Smart Grid Innovations LLC':
                        seq_code = 'stock.picking.grn.sgi'
                    else:
                        raise UserError("❌ GRN sequence not configured for this company.")

                if seq_code:
                    new_name = self.env['ir.sequence'].with_company(company).next_by_code(seq_code)
                    if not new_name:
                        raise UserError(f"❌ Sequence '{seq_code}' not found or misconfigured for company '{company.name}'.")

                    existing = self.search([
                        ('name', '=', new_name),
                        ('company_id', '=', company.id)
                    ], limit=1)

                    if existing:
                        raise UserError(
                            _("❌ The generated Picking name '%s' already exists in company '%s'. Please check the sequence configuration.") % (
                                new_name, company.name))

                    vals['name'] = new_name

        return super(StockPicking, self).create(vals_list)
