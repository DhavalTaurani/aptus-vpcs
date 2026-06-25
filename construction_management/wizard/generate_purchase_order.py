# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class GeneratePurchaseOrder(models.TransientModel):
    _name = 'construction.generate.purchase.order'
    _description = 'Generate Purchase Order from BOQ'

    @api.model
    def default_get(self, fields_list):
        res = super(GeneratePurchaseOrder, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model')
        
        if active_ids and active_model == 'project.task':
            tasks = self.env['project.task'].browse(active_ids)
            # Filter for BOQ items that are approved and not yet billed
            boq_tasks = tasks.filtered(lambda t: t.is_boq_item and t.boq_state == 'approved' and not t.is_billed)
            if boq_tasks:
                res['task_ids'] = [(6, 0, boq_tasks.ids)]
                projects = boq_tasks.mapped('project_id')
                if len(projects) == 1:
                    res['project_id'] = projects.id
        return res

    project_id = fields.Many2one(
        'project.project', 
        'Construction Project', 
        domain="[('is_construction', '=', True)]"
    )
    task_ids = fields.Many2many(
        'project.task', 
        string='BOQ Items',
        required=True,
        domain="[('is_boq_item', '=', True), ('boq_state', '=', 'approved'), ('is_billed', '=', False), ('purchase_order_count', '=', 0), ('project_id', '=?', project_id)]"
    )
    
    create_new_po = fields.Boolean(
        'Create New Purchase Order(s)',
        default=True,
        help="Check this to create new Purchase Orders. Uncheck to add to an existing one."
    )
    
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Existing Purchase Order',
        domain="[('state', 'in', ('draft', 'sent'))]",
        help="Select an existing PO to add the lines to. The vendor will be ignored."
    )
    
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor (Optional)',
        domain="[('is_company', '=', True), ('supplier_rank', '>', 0)]",
        help="If you select a vendor, all items will be added to a single PO for that vendor. "
            "If you leave it blank, Odoo will group items by their default vendor and create multiple POs."
    )
    
    date_planned = fields.Date(
        'Planned Date',
        default=fields.Date.today(),
        required=True
    )

    @api.onchange('project_id')
    def _onchange_project_id(self):
        # Clear task_ids when project changes and update domain
        self.task_ids = [(5, 0, 0)]
        if self.project_id:
            return {
                'domain': {
                    'task_ids': [
                        ('project_id', '=', self.project_id.id), 
                        ('is_boq_item', '=', True), 
                        ('boq_state', '=', 'approved'),
                        ('is_billed', '=', False)
                    ]
                }
            }
        return {'domain': {'task_ids': [('id', '=', False)]}}

    @api.onchange('task_ids')
    def _onchange_task_ids(self):
        if self.task_ids and self.create_new_po and not self.vendor_id:
            # Try to suggest a common vendor if all selected BOQ items have one
            all_vendors = set()
            for task in self.task_ids:
                if task.cost_code_id and task.cost_code_id.product_template_id:
                    product_vendors = task.cost_code_id.product_template_id.seller_ids.mapped('partner_id')
                    if product_vendors:
                        all_vendors.update(product_vendors.ids)
            
            # If all tasks share a common vendor, suggest it
            if len(all_vendors) == 1:
                self.vendor_id = list(all_vendors)[0]

    def _prepare_po_line_vals(self, task, purchase_order):
        if not task.cost_code_id:
            raise UserError(_("BOQ Item '%s' must have a cost code assigned.") % task.name)
        
        if not task.cost_code_id.product_template_id:
            raise UserError(_("Cost code '%s' for BOQ Item '%s' must have a product template assigned.") % (task.cost_code_id.name, task.name))
        
        product = task.cost_code_id.product_template_id.product_variant_id
        if not product:
            raise UserError(_("Product variant not found for cost code '%s' in BOQ Item '%s'.") % (task.cost_code_id.name, task.name))

        quantity = task.revised_quantity if task.revised_quantity > 0 else task.estimated_quantity
        if quantity <= 0:
            raise UserError(_("BOQ Item '%s' must have a positive quantity (revised: %s, estimated: %s).") % (task.name, task.revised_quantity, task.estimated_quantity))

        return {
            'order_id': purchase_order.id,
            'product_id': product.id,
            'name': f"[{task.project_id.name}] {product.name}",
            'product_qty': quantity,
            'price_unit': task.unit_cost or 0.0,
            'product_uom_id': product.uom_id.id,
            'date_planned': self.date_planned,
            'boq_task_id': task.id,
            'cost_code_id': task.cost_code_id.id,
            'construction_project_id': task.project_id.id,
        }

    def _add_to_existing_po(self):
        if not self.purchase_order_id:
            raise UserError(_("Please select an Existing Purchase Order."))
        
        purchase_order = self.purchase_order_id
        po_line_obj = self.env['purchase.order.line']

        for task in self.task_ids:
            line_vals = self._prepare_po_line_vals(task, purchase_order)
            if not line_vals:
                continue

            # Check if a line for this product and task already exists
            existing_line = purchase_order.order_line.filtered(
                lambda l: l.product_id.id == line_vals['product_id'] and l.boq_task_id.id == task.id
            )
            if existing_line:
                existing_line.product_qty += line_vals['product_qty']
            else:
                po_line_obj.create(line_vals)
        
        return [purchase_order]

    def _create_new_pos(self):
        po_obj = self.env['purchase.order']
        po_line_obj = self.env['purchase.order.line']
        purchase_orders = self.env['purchase.order']

        if self.vendor_id:
            # Create one PO for the selected vendor
            po = po_obj.create({
                'partner_id': self.vendor_id.id,
                'date_order': fields.Datetime.now(),
                'date_planned': self.date_planned,
                'origin': self.project_id.name if self.project_id else '',
            })
            purchase_orders |= po
            for task in self.task_ids:
                line_vals = self._prepare_po_line_vals(task, po)
                if line_vals:
                    po_line_obj.create(line_vals)
        else:
            # Group tasks by vendor and create multiple POs
            vendor_tasks = {}
            for task in self.task_ids:
                if not task.cost_code_id or not task.cost_code_id.product_template_id:
                    raise UserError(_("BOQ item '%s' must have a cost code with product template assigned.") % task.name)
                
                product_template = task.cost_code_id.product_template_id
                if not product_template.seller_ids:
                    raise UserError(_("Product '%s' for BOQ item '%s' does not have a configured vendor.") % (product_template.name, task.name))
                
                vendor = product_template.seller_ids[0].partner_id
                if vendor not in vendor_tasks:
                    vendor_tasks[vendor] = []
                vendor_tasks[vendor].append(task)

            if not vendor_tasks:
                raise UserError(_("No purchase orders to generate. Check quantities and product vendors for the selected BOQ items."))

            for vendor, tasks in vendor_tasks.items():
                po = po_obj.create({
                    'partner_id': vendor.id,
                    'date_order': fields.Datetime.now(),
                    'date_planned': self.date_planned,
                    'origin': self.project_id.name if self.project_id else '',
                })
                purchase_orders |= po
                for task in tasks:
                    line_vals = self._prepare_po_line_vals(task, po)
                    if line_vals:
                        po_line_obj.create(line_vals)
        
        return purchase_orders

    def generate_purchase_order(self):
        self.ensure_one()
        if any(task.is_billed for task in self.task_ids):
            raise UserError(_("You cannot generate a purchase order for a BOQ item that has already been billed."))
        if not self.task_ids:
            raise UserError(_("Please select at least one BOQ Item."))

        if self.create_new_po:
            purchase_orders = self._create_new_pos()
        else:
            purchase_orders = self._add_to_existing_po()

        if not purchase_orders:
            raise UserError(_("No Purchase Order lines were generated. Check the quantities and configurations of the selected BOQ items."))

        # Return an action to display the created/updated purchase orders
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")
        if len(purchase_orders) > 1:
            action['domain'] = [('id', 'in', purchase_orders.ids)]
        elif purchase_orders:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = purchase_orders.id[0] if isinstance(purchase_orders.id, list) else purchase_orders.id
        else:
            # No POs created, maybe show a message or just close the wizard
            return {'type': 'ir.actions.act_window_close'}
            
        return action