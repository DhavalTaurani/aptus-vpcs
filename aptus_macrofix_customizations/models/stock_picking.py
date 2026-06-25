from odoo import fields, models, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = "stock.picking"


    previous_name = fields.Char(string="Previous Sequence", readonly=True)

    def write(self, vals):
        for picking in self:
            if 'name' in vals and picking.name not in ['/', False, 'New']:
                if not picking.previous_name:
                    picking.previous_name = picking.name
                else:
                    raise UserError("❌ Old sequence already updated.")
        return super().write(vals)