# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Construction-specific fields
    is_construction_item = fields.Boolean('Construction Item', default=False,
                                        help="Check if this product is used in construction projects")
    construction_cost_code_id = fields.Many2one('construction.cost.code', 'Construction Cost Code',
                                                help="Associated construction cost code")
    construction_cost_type = fields.Selection(related='construction_cost_code_id.cost_type',
                                            string='Construction Cost Type', store=True, readonly=True)
    
    # Construction template integration
    construction_template_id = fields.Many2one(
        'construction.project.template', 
        'Construction Template',
        help="Construction project template to apply when this product creates a project"
    )
    
    # BOQ and estimation fields
    is_boq_item = fields.Boolean('BOQ Item', default=False,
                                help="Check if this product can be used as a BOQ item")
    boq_category = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('equipment', 'Equipment'),
        ('service', 'Service')
    ], string='BOQ Category', help="Category for BOQ classification")
    
    # Construction-specific pricing
    construction_unit_cost = fields.Monetary('Construction Unit Cost', currency_field='currency_id',
                                            help="Standard construction unit cost")
    construction_markup_percentage = fields.Float('Construction Markup %', default=0.0,
                                                help="Markup percentage for construction pricing")
    construction_selling_price = fields.Monetary('Construction Selling Price', 
                                                currency_field='currency_id',
                                                compute='_compute_construction_selling_price',
                                                store=True,
                                                help="Computed selling price with markup")
    
    # Waste and loss factors
    waste_factor = fields.Float('Waste Factor %', default=0.0,
                                help="Expected waste percentage for this material")
    loss_factor = fields.Float('Loss Factor %', default=0.0,
                                help="Expected loss percentage during construction")
    total_factor = fields.Float('Total Factor %', compute='_compute_total_factor', store=True,
                                help="Combined waste and loss factor")
    
    # Supplier and procurement information
    preferred_supplier_id = fields.Many2one('res.partner', 'Preferred Supplier',
                                            domain=[('is_company', '=', True), ('supplier_rank', '>', 0)],
                                            help="Preferred supplier for this construction item")
    lead_time_days = fields.Integer('Lead Time (Days)', default=0,
                                    help="Standard lead time for procurement")
    minimum_order_qty = fields.Float('Minimum Order Quantity', default=1.0,
                                    help="Minimum quantity for ordering")
    
    # Usage tracking
    construction_usage_count = fields.Integer('Construction Usage Count',
                                            compute='_compute_construction_usage_count',
                                            help="Number of times used in construction projects")
    last_construction_use = fields.Datetime('Last Construction Use',
                                            compute='_compute_last_construction_use',
                                            help="Last time used in construction")
    
    # Computed fields
    @api.depends('construction_unit_cost', 'construction_markup_percentage')
    def _compute_construction_selling_price(self):
        """Compute construction selling price with markup"""
        for product in self:
            if product.construction_unit_cost and product.construction_markup_percentage:
                markup_amount = product.construction_unit_cost * (product.construction_markup_percentage / 100)
                product.construction_selling_price = product.construction_unit_cost + markup_amount
            else:
                product.construction_selling_price = product.construction_unit_cost
    
    @api.depends('waste_factor', 'loss_factor')
    def _compute_total_factor(self):
        """Compute total waste and loss factor"""
        for product in self:
            product.total_factor = product.waste_factor + product.loss_factor
    
    def _compute_construction_usage_count(self):
        """Compute usage count in construction projects"""
        for product in self:
            # Count usage in project tasks (BOQ items)
            task_count = self.env['project.task'].search_count([
                ('product_id', 'in', product.product_variant_ids.ids)
            ])
            product.construction_usage_count = task_count
    
    def _compute_last_construction_use(self):
        """Compute last construction usage date"""
        for product in self:
            last_task = self.env['project.task'].search([
                ('product_id', 'in', product.product_variant_ids.ids)
            ], order='write_date desc', limit=1)
            product.last_construction_use = last_task.write_date if last_task else False
    
    # Constraints and validations
    @api.constrains('construction_markup_percentage')
    def _check_construction_markup(self):
        """Validate construction markup percentage"""
        for product in self:
            if product.construction_markup_percentage < 0:
                raise ValidationError(_('Construction markup percentage cannot be negative.'))
            if product.construction_markup_percentage > 1000:
                raise ValidationError(_('Construction markup percentage cannot exceed 1000%.'))
    
    @api.constrains('waste_factor', 'loss_factor')
    def _check_waste_loss_factors(self):
        """Validate waste and loss factors"""
        for product in self:
            if product.waste_factor < 0 or product.loss_factor < 0:
                raise ValidationError(_('Waste and loss factors cannot be negative.'))
            if product.waste_factor > 100 or product.loss_factor > 100:
                raise ValidationError(_('Waste and loss factors cannot exceed 100%.'))
    
    @api.constrains('lead_time_days', 'minimum_order_qty')
    def _check_procurement_fields(self):
        """Validate procurement fields"""
        for product in self:
            if product.lead_time_days < 0:
                raise ValidationError(_('Lead time cannot be negative.'))
            if product.minimum_order_qty <= 0:
                raise ValidationError(_('Minimum order quantity must be positive.'))
    
    # Onchange methods
    @api.onchange('is_construction_item')
    def _onchange_is_construction_item(self):
        """Handle construction item flag changes"""
        if not self.is_construction_item:
            self.construction_cost_code_id = False
            self.is_boq_item = False
            self.boq_category = False
    
    @api.onchange('construction_cost_code_id')
    def _onchange_construction_cost_code(self):
        """Auto-populate fields based on cost code"""
        if self.construction_cost_code_id:
            self.is_construction_item = True
            
            # Set BOQ category based on cost type
            cost_type_mapping = {
                'material': 'material',
                'labour': 'labour',
                'equipment': 'equipment',
                'subcontractor': 'service',
                'miscellaneous': 'service',
                'overhead': 'service'
            }
            self.boq_category = cost_type_mapping.get(self.construction_cost_code_id.cost_type, 'material')
            
            # Set default UOM if not set
            if not self.uom_id and self.construction_cost_code_id.default_uom_id:
                self.uom_id = self.construction_cost_code_id.default_uom_id
                self.uom_po_id = self.construction_cost_code_id.default_uom_id
            
            # Set standard cost if available
            if self.construction_cost_code_id.standard_cost and not self.construction_unit_cost:
                self.construction_unit_cost = self.construction_cost_code_id.standard_cost
    
    @api.onchange('categ_id')
    def _onchange_category_suggest_cost_code(self):
        """Suggest cost code based on product category"""
        if self.categ_id and self.is_construction_item and not self.construction_cost_code_id:
            # Find cost code associated with this category
            cost_code = self.env['construction.cost.code'].search([
                ('product_category_id', '=', self.categ_id.id)
            ], limit=1)
            if cost_code:
                self.construction_cost_code_id = cost_code
    
    # Business methods
    def action_view_construction_usage(self):
        """Action to view construction usage"""
        self.ensure_one()
        return {
            'name': _('Construction Usage'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [('product_id', 'in', self.product_variant_ids.ids)],
            'context': {'default_product_id': self.product_variant_ids[0].id if self.product_variant_ids else False},
        }
    
    def generate_cost_code_from_category(self):
        """Generate cost code based on product category hierarchy"""
        self.ensure_one()
        if not self.categ_id:
            return False
        
        # Build cost code from category hierarchy
        categories = []
        category = self.categ_id
        while category:
            categories.insert(0, category)
            category = category.parent_id
        
        # Generate code parts
        code_parts = []
        for cat in categories:
            # Use first 3 characters of category name, uppercase
            code_part = ''.join(c for c in cat.name if c.isalnum())[:3].upper()
            if code_part:
                code_parts.append(code_part)
        
        if not code_parts:
            return False
        
        # Create hierarchical cost codes if they don't exist
        parent_cost_code = None
        for i, (category, code_part) in enumerate(zip(categories, code_parts)):
            # Build full code up to this level
            full_code = '.'.join(code_parts[:i+1])
            
            # Check if cost code exists
            cost_code = self.env['construction.cost.code'].search([
                ('code', '=', full_code)
            ], limit=1)
            
            if not cost_code:
                # Determine cost type from category or parent
                cost_type = 'material'  # Default
                if 'labour' in category.name.lower() or 'labor' in category.name.lower():
                    cost_type = 'labour'
                elif 'equipment' in category.name.lower():
                    cost_type = 'equipment'
                elif 'service' in category.name.lower() or 'subcontractor' in category.name.lower():
                    cost_type = 'subcontractor'
                elif parent_cost_code:
                    cost_type = parent_cost_code.cost_type
                
                # Create cost code
                cost_code = self.env['construction.cost.code'].create({
                    'name': category.name,
                    'code': full_code,
                    'description': f'Auto-generated from product category: {category.name}',
                    'cost_type': cost_type,
                    'parent_id': parent_cost_code.id if parent_cost_code else False,
                    'product_category_id': category.id,
                    'is_category': i < len(categories) - 1,  # All but last are categories
                })
            
            parent_cost_code = cost_code
        
        return parent_cost_code
    
    def update_construction_pricing(self):
        """Update construction pricing from cost code standards"""
        for product in self:
            if product.construction_cost_code_id:
                if product.construction_cost_code_id.standard_cost:
                    product.construction_unit_cost = product.construction_cost_code_id.standard_cost
                if product.construction_cost_code_id.standard_price:
                    product.list_price = product.construction_cost_code_id.standard_price


class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    # Construction integration
    is_construction_category = fields.Boolean('Construction Category', default=False,
                                            help="Check if this category is used for construction items")
    construction_cost_code_id = fields.Many2one('construction.cost.code', 'Associated Cost Code',
                                                help="Cost code associated with this category")
    construction_cost_type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('equipment', 'Equipment'),
        ('subcontractor', 'Subcontractor'),
        ('miscellaneous', 'Miscellaneous'),
        ('overhead', 'Overhead')
    ], string='Construction Cost Type', help="Default cost type for products in this category")
    
    # Default construction settings
    default_waste_factor = fields.Float('Default Waste Factor %', default=0.0,
                                        help="Default waste factor for products in this category")
    default_loss_factor = fields.Float('Default Loss Factor %', default=0.0,
                                        help="Default loss factor for products in this category")
    default_markup_percentage = fields.Float('Default Markup %', default=0.0,
                                            help="Default markup percentage for construction pricing")
    
    # Usage tracking
    construction_product_count = fields.Integer('Construction Products',
                                                compute='_compute_construction_product_count',
                                                help="Number of construction products in this category")
    
    @api.depends('name') # Depend on name to trigger re-computation if category name changes
    def _compute_construction_product_count(self):
        """Compute number of construction products in category"""
        for category in self:
            category.construction_product_count = self.env['product.template'].search_count([
                ('categ_id', 'child_of', category.id),
                ('is_construction_item', '=', True)
            ])
    
    @api.onchange('is_construction_category')
    def _onchange_is_construction_category(self):
        """Handle construction category flag changes"""
        if not self.is_construction_category:
            self.construction_cost_code_id = False
            self.construction_cost_type = False
    
    def action_generate_cost_code(self):
        """Generate cost code for this category"""
        self.ensure_one()
        if self.construction_cost_code_id:
            return  # Already has cost code
        
        # Generate code from category hierarchy
        categories = []
        category = self
        while category:
            categories.insert(0, category)
            category = category.parent_id
        
        # Generate code parts
        code_parts = []
        for cat in categories:
            code_part = ''.join(c for c in cat.name if c.isalnum())[:3].upper()
            if code_part:
                code_parts.append(code_part)
        
        if not code_parts:
            return
        
        full_code = '.'.join(code_parts)
        
        # Create cost code
        cost_code = self.env['construction.cost.code'].create({
            'name': self.name,
            'code': full_code,
            'description': f'Generated from product category: {self.name}',
            'cost_type': self.construction_cost_type or 'material',
            'product_category_id': self.id,
            'is_category': True,
        })
        
        self.construction_cost_code_id = cost_code
        
        return {
            'name': _('Generated Cost Code'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.cost.code',
            'res_id': cost_code.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_view_construction_products(self):
        """Action to view construction products in this category"""
        self.ensure_one()
        return {
            'name': _('Construction Products'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('categ_id', 'child_of', self.id), ('is_construction_item', '=', True)],
            'context': {
                'default_categ_id': self.id,
                'default_is_construction_item': True,
                'default_construction_cost_type': self.construction_cost_type,
            },
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Inherit construction fields from template
    is_construction_item = fields.Boolean(related='product_tmpl_id.is_construction_item', readonly=True)
    construction_cost_code_id = fields.Many2one(related='product_tmpl_id.construction_cost_code_id', readonly=True)
    construction_cost_type = fields.Selection(related='product_tmpl_id.construction_cost_type', readonly=True)
    
    def action_view_boq_usage(self):
        """Action to view BOQ usage for this product variant"""
        self.ensure_one()
        return {
            'name': _('BOQ Usage'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id), ('is_boq_item', '=', True)],
            'context': {'default_product_id': self.id},
        }
