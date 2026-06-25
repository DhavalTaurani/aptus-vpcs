from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    _description = 'Purchase order'

    delivery_terms = fields.Char('Delivery Terms')
    rel_sales_order = fields.Many2one('sale.order', string='Rel Sale Order')
    customer_id = fields.Many2one(comodel_name='res.partner',string='Customer')
    customer_contact_id = fields.Many2one(comodel_name='res.partner',string='Customer Contact')
    customer_contact_email = fields.Char(string="Contact's Email")
    customer_contact_phone = fields.Char(string="Contact's Mobile")
    remarks = fields.Text(string='Remarks')
    stamp_selection = fields.Selection(selection=[('oriental_oryx_stamp', 'Main Stamp'), ('aptus_stamp', 'Aptus Stamp'),], string="Select Stamp")

    @api.onchange('customer_contact_id')
    def _onchange_customer_contact_id(self):
        for rec in self:
            rec.customer_contact_email = rec.customer_contact_id.email
            rec.customer_contact_phone = rec.customer_contact_id.phone

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'


    project_id = fields.Many2one('project.project', string='Project')

    def _get_product_purchase_description(self, product_lang):
        self.ensure_one()
        name = product_lang.name  # Use only the product name, not display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase
        return name