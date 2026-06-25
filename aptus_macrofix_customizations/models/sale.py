from odoo import models, fields, api

class DefTandC(models.Model):
    _name = 'def.tandc'

    name = fields.Char(required=True)
    terms_and_conditions = fields.Html(required=True)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Sales order'

    delivery = fields.Char('Delivery')

    stamp_selection = fields.Selection([
        ('oriental_oryx_stamp', 'Main Stamp'),
        ('aptus_stamp', 'Aptus Stamp'),
    ], string="Select Stamp")

    customer_po_date = fields.Date('Client PO date')
    tandc_id = fields.Many2one(comodel_name='def.tandc', string="Terms & Conditions")

    @api.onchange('tandc_id')
    def fill_terms_and_conditions_in_so(self):
        for rec in self:
            if rec.tandc_id:
                rec.note = rec.tandc_id.terms_and_conditions
            else:
                rec.note = ''

    def _find_mail_template(self):
        self.ensure_one()
        return self.env.ref('aptus_macrofix_customizations.email_template_edi_sale_inherit')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    project_id = fields.Many2one('project.project', string='Project')

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            if not line.product_id:
                continue
            lang = line.order_id._get_lang()
            if lang != self.env.lang:
                line = line.with_context(lang=lang)
            line.name = line.product_id.description_sale if line.product_id.description_sale else line.product_id.name