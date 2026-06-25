from odoo import models, api
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('rel_sales_order')
    def _onchange_rel_sales_order(self):
        """Clears existing lines and adds fresh lines from SO"""
        if not self.rel_sales_order:
            return

        # Unlink/Clear all existing lines first
        self.order_line = [(5, 0, 0)]
        
        new_lines = []
        for sol in self.rel_sales_order.order_line:
            if not sol.display_type and sol.product_id:
                line_values = self._prepare_po_line_from_so_line(sol)
                new_lines.append((0, 0, line_values))
        
        if new_lines:
            self.order_line = new_lines

    def action_sync_so_lines(self):
        """Updates existing lines and adds missing products from SO"""
        self.ensure_one()
        if not self.rel_sales_order:
            return
        if self.locked:
            raise UserError("Cannot sync lines on a locked Purchase Order.")
        else:
            for sol in self.rel_sales_order.order_line:
                if not sol.display_type and sol.product_id:
                    line_values = self._prepare_po_line_from_so_line(sol)
                    
                    # Search for existing product in the PO lines
                    existing_line = self.order_line.filtered(lambda l: l.product_id == sol.product_id)
                    
                    if existing_line:
                        # Update only the first occurrence found
                        existing_line[0].write(line_values)
                    else:
                        # Append new product if it doesn't exist
                        self.order_line = [(0, 0, line_values)]

    def _prepare_po_line_from_so_line(self, sol):
        """Helper method to map fields and find Purchase Taxes"""
        purchase_tax_ids = []
        for s_tax in sol.tax_ids:
            p_tax = self.env['account.tax'].search([
                ('amount', '=', s_tax.amount),
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', s_tax.company_id.id)
            ], limit=1)
            if p_tax:
                purchase_tax_ids.append(p_tax.id)

        return {
            'project_id': sol.project_id.id,
            'product_id': sol.product_id.id,
            'name': sol.name,
            'product_qty': sol.product_uom_qty,
            'product_uom_id': sol.product_uom_id.id,
            'price_unit': sol.price_unit,
            'tax_ids': [(6, 0, purchase_tax_ids)],
            'analytic_distribution': sol.analytic_distribution,
            'discount': sol.discount,
        }
        