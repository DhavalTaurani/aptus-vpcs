from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand = fields.Char(string='Brand')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    brand = fields.Char(related='product_tmpl_id.brand', store=True, readonly=False)
