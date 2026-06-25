# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ConstructionPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super(ConstructionPurchaseOrder, self).button_confirm()
        for order in self:
            for line in order.order_line:
                if line.boq_task_id and abs(line.price_variance) > 0.01:
                    # Post a message on the project chatter
                    message = f"Price variance of {line.price_variance:.2f} {order.currency_id.symbol} detected for BOQ item {line.boq_task_id.name} in purchase order {order.name}."
                    order.project_id.message_post(body=message)
        return res
