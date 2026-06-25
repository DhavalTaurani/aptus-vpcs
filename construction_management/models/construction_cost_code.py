# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ConstructionCostCode(models.Model):
    _name = 'construction.cost.code'
    _description = 'Construction Cost Code'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code'
    _rec_name = 'display_name'
    
    # Basic identification fields
    name = fields.Char('Name', required=True, tracking=True, translate=True)
    code = fields.Char('Code', required=True, index=True, tracking=True,
                        help="Unique identifier for the cost code")
    description = fields.Text('Description', translate=True,
                            help="Detailed description of the cost code")
    
    # Display name for better UX
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    
    # Hierarchical structure
    parent_id = fields.Many2one('construction.cost.code', 'Parent Cost Code',
                                index=True, ondelete='cascade',
                                help="Parent cost code for hierarchical organization")
    child_ids = fields.One2many('construction.cost.code', 'parent_id', 'Child Cost Codes')
    child_count = fields.Integer('Child Count', compute='_compute_child_count')
    level = fields.Integer('Level', compute='_compute_level', store=True,
                        help="Hierarchy level (0 for root level)")
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True, recursive=True,
                                help="Full hierarchical name")

    @api.depends('child_ids')
    def _compute_child_count(self):
        for record in self:
            record.child_count = len(record.child_ids)

    # Cost classification
    cost_type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('equipment', 'Equipment'),
        ('subcontractor', 'Subcontractor'),
        ('miscellaneous', 'Miscellaneous'),
        ('overhead', 'Overhead')
    ], string='Cost Type', required=True, tracking=True,
        help="Primary classification of the cost type")
    
    # Product integration
    product_template_id = fields.Many2one('product.template', 'Product Template',
                                        help="Associated product template")
    product_category_id = fields.Many2one('product.category', 'Product Category',
                                        help="Associated product category")
    
    # Default values and standards
    default_uom_id = fields.Many2one('uom.uom', 'Default Unit of Measure',
                                    help="Default unit of measure for this cost code")
    standard_cost = fields.Monetary('Standard Cost', currency_field='currency_id',
                                    help="Standard cost per unit")
    standard_price = fields.Monetary('Standard Price', currency_field='currency_id',
                                    help="Standard selling price per unit")
    currency_id = fields.Many2one('res.currency', 'Currency',
                                default=lambda self: self.env.company.currency_id)
    
    # Status and control
    active = fields.Boolean('Active', default=True, tracking=True,
                            help="Uncheck to archive the cost code")
    is_category = fields.Boolean('Is Category', default=False,
                                help="Check if this is a category (parent) cost code")
    
    # Usage statistics
    usage_count = fields.Integer('Usage Count', compute='_compute_usage_count',
                                help="Number of times this cost code is used")
    last_used_date = fields.Datetime('Last Used Date', compute='_compute_last_used_date',
                                    help="Date when this cost code was last used")
    
    # Company and multi-company support
    company_id = fields.Many2one('res.company', 'Company',
                                default=lambda self: self.env.company,
                                help="Company this cost code belongs to")
    
    # Computed fields
    @api.depends('name', 'code')
    def _compute_display_name(self):
        """Compute display name combining code and name"""
        for record in self:
            if record.code and record.name:
                record.display_name = f"[{record.code}] {record.name}"
            elif record.code:
                record.display_name = record.code
            else:
                record.display_name = record.name or ''
    
    @api.depends('parent_id')
    def _compute_level(self):
        """Compute hierarchy level"""
        for record in self:
            level = 0
            parent = record.parent_id
            while parent:
                level += 1
                parent = parent.parent_id
            record.level = level
    
    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        """Compute complete hierarchical name"""
        for record in self:
            if record.parent_id:
                record.complete_name = f"{record.parent_id.complete_name} / {record.name}"
            else:
                record.complete_name = record.name
    
    def _compute_usage_count(self):
        """Compute usage count from project tasks"""
        for record in self:
            # Count usage in project tasks (BOQ items)
            task_count = self.env['project.task'].search_count([
                ('cost_code_id', '=', record.id)
            ])
            record.usage_count = task_count
    
    def _compute_last_used_date(self):
        """Compute last used date from project tasks"""
        for record in self:
            last_task = self.env['project.task'].search([
                ('cost_code_id', '=', record.id)
            ], order='write_date desc', limit=1)
            record.last_used_date = last_task.write_date if last_task else False
    
    # Constraints and validations
    _code_company_unique = models.Constraint(
        'UNIQUE(code, company_id)',
        'Cost code must be unique per company!',
    )
    
    _standard_cost_positive = models.Constraint(
        'CHECK(standard_cost >= 0)',
        'Standard cost must be positive!',
    )
    
    _standard_price_positive = models.Constraint(
        'CHECK(standard_price >= 0)', 
        'Standard price must be positive!',
    )
    
    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        """Prevent recursive parent relationships"""
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive cost code hierarchies.'))
    
    @api.constrains('parent_id', 'cost_type')
    def _check_parent_cost_type(self):
        """Ensure child cost codes have compatible cost types with parent"""
        for record in self:
            if record.parent_id and record.parent_id.cost_type != record.cost_type:
                raise ValidationError(_(
                    'Child cost code must have the same cost type as parent. '
                    'Parent: %s, Child: %s'
                ) % (record.parent_id.cost_type, record.cost_type))
    
    @api.constrains('code')
    def _check_code_format(self):
        """Validate cost code format"""
        for record in self:
            if not record.code:
                continue
            # Basic format validation - alphanumeric with dots, dashes, and underscores
            import re
            if not re.match(r'^[A-Za-z0-9._-]+$', record.code):
                raise ValidationError(_(
                    'Cost code can only contain letters, numbers, dots, dashes, and underscores.'
                ))
    
    @api.constrains('is_category', 'child_ids')
    def _check_category_consistency(self):
        """Ensure category flag is consistent with having children"""
        for record in self:
            if record.child_ids and not record.is_category:
                raise ValidationError(_(
                    'Cost codes with children must be marked as categories.'
                ))
    
    # CRUD operations and business logic
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle automatic categorization"""
        # Auto-set is_category if parent_id is provided
        for vals in vals_list:
            if vals.get('parent_id'):
                parent = self.browse(vals['parent_id'])
                if not parent.is_category:
                    parent.write({'is_category': True})
        
        records = super().create(vals_list)
        
        # Log creation in chatter
        for record in records:
            record.message_post(
                body=_('Cost code created with type: %s') % record.cost_type,
                message_type='notification'
            )
        
        return records
    
    def write(self, vals):
        """Override write to handle hierarchy changes"""
        # Handle parent changes
        if 'parent_id' in vals:
            old_parents = self.mapped('parent_id')
            
        result = super().write(vals)
        
        # Update parent category flags if needed
        if 'parent_id' in vals:
            # Set new parent as category
            new_parent = self.env['construction.cost.code'].browse(vals['parent_id'])
            if new_parent and not new_parent.is_category:
                new_parent.write({'is_category': True})
            
            # Check if old parents still need category flag
            for old_parent in old_parents:
                if old_parent and not old_parent.child_ids:
                    old_parent.write({'is_category': False})
        
        return result
    
    def unlink(self):
        """Override unlink to handle cascading and validation"""
        # Check if cost codes are in use
        for record in self:
            if record.usage_count > 0:
                raise UserError(_(
                    'Cannot delete cost code "%s" because it is being used in %d project tasks. '
                    'Archive it instead.'
                ) % (record.display_name, record.usage_count))
        
        # Update parent category flags
        parents_to_check = self.mapped('parent_id')
        
        result = super().unlink()
        
        # Check if parents still need category flag
        for parent in parents_to_check:
            if parent and not parent.child_ids:
                parent.write({'is_category': False})
        
        return result
    
    # Business methods
    def name_get(self):
        """Custom name_get to show code and name"""
        result = []
        for record in self:
            if record.code and record.name:
                name = f"[{record.code}] {record.name}"
            elif record.code:
                name = record.code
            else:
                name = record.name or ''
            result.append((record.id, name))
        return result
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Enhanced name search to include code and description"""
        args = args or []
        domain = []
        
        if name:
            domain = ['|', '|', '|',
                    ('name', operator, name),
                    ('code', operator, name),
                    ('description', operator, name),
                    ('complete_name', operator, name)]
        
        return self.search(domain + args, limit=limit).name_get()
    
    def get_children_recursive(self):
        """Get all children recursively"""
        children = self.env['construction.cost.code']
        for record in self:
            children |= record.child_ids
            if record.child_ids:
                children |= record.child_ids.get_children_recursive()
        return children
    
    def get_root_parent(self):
        """Get the root parent of the hierarchy"""
        self.ensure_one()
        parent = self
        while parent.parent_id:
            parent = parent.parent_id
        return parent
    
    def generate_child_code(self, suffix):
        """Generate a child code based on parent code"""
        self.ensure_one()
        if not self.code:
            raise UserError(_('Parent cost code must have a code to generate child codes.'))
        
        # Find next available number
        existing_codes = self.child_ids.mapped('code')
        base_code = f"{self.code}.{suffix}"
        
        counter = 1
        new_code = base_code
        while new_code in existing_codes:
            new_code = f"{base_code}.{counter:02d}"
            counter += 1
        
        return new_code
    
    def action_view_usage(self):
        """Action to view where this cost code is used"""
        self.ensure_one()
        return {
            'name': _('Cost Code Usage'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [('cost_code_id', '=', self.id)],
            'context': {'default_cost_code_id': self.id},
        }

    def action_view_children(self):
        self.ensure_one()
        return {
            'name': _('Child Cost Codes'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.cost.code',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id},
        }
    
    def action_duplicate_with_children(self):
        """Duplicate cost code with all its children"""
        self.ensure_one()
        
        def duplicate_recursive(cost_code, parent=None):
            # Create copy of current cost code
            vals = {
                'name': f"{cost_code.name} (Copy)",
                'code': f"{cost_code.code}_COPY",
                'description': cost_code.description,
                'cost_type': cost_code.cost_type,
                'parent_id': parent.id if parent else False,
                'product_category_id': cost_code.product_category_id.id,
                'default_uom_id': cost_code.default_uom_id.id,
                'standard_cost': cost_code.standard_cost,
                'standard_price': cost_code.standard_price,
                'is_category': cost_code.is_category,
                'company_id': cost_code.company_id.id,
            }
            
            new_cost_code = self.create(vals)
            
            # Recursively duplicate children
            for child in cost_code.child_ids:
                duplicate_recursive(child, new_cost_code)
            
            return new_cost_code
        
        new_cost_code = duplicate_recursive(self)
        
        return {
            'name': _('Duplicated Cost Code'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.cost.code',
            'res_id': new_cost_code.id,
            'view_mode': 'form',
            'target': 'current',
        }