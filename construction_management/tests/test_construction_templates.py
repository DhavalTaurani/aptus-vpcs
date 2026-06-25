# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestConstructionTemplates(TransactionCase):
    """Test suite for construction template functionality"""
    
    def setUp(self):
        super().setUp()
        
        # Create test cost codes
        self.cost_code_material = self.env['construction.cost.code'].create({
            'name': 'Test Materials',
            'code': 'TEST-MAT',
            'cost_type': 'material',
        })
        
        self.cost_code_labour = self.env['construction.cost.code'].create({
            'name': 'Test Labour',
            'code': 'TEST-LAB',
            'cost_type': 'labour',
        })
        
        # Create test construction template
        self.construction_template = self.env['construction.project.template'].create({
            'name': 'Test Construction Template',
            'construction_category': 'general',
            'description': 'Test template for construction projects',
            'state': 'approved',
        })
        
        # Create test task templates
        self.task_template_parent = self.env['construction.task.template'].create({
            'name': 'Foundation Work',
            'template_id': self.construction_template.id,
            'sequence': 10,
            'is_boq_item': True,
            'boq_code': 'FOUND-001',
            'estimated_quantity': 100.0,
            'unit_cost': 50.0,
            'cost_code_id': self.cost_code_material.id,
        })
        
        self.task_template_child = self.env['construction.task.template'].create({
            'name': 'Concrete Pouring',
            'template_id': self.construction_template.id,
            'parent_template_id': self.task_template_parent.id,
            'sequence': 11,
            'is_boq_item': True,
            'boq_code': 'FOUND-002',
            'estimated_quantity': 50.0,
            'unit_cost': 75.0,
            'cost_code_id': self.cost_code_labour.id,
        })
        
        # Create test BOQ template
        self.boq_template = self.env['construction.boq.template'].create({
            'name': 'Concrete Foundation',
            'code': 'BOQ-FOUND-001',
            'template_id': self.construction_template.id,
            'task_template_id': self.task_template_parent.id,
            'quantity': 100.0,
            'unit_of_measure_id': self.env.ref('uom.product_uom_cubic_meter').id,
            'unit_cost': 150.0,
            'cost_code_id': self.cost_code_material.id,
        })
        
        # Create test service product
        self.service_product = self.env['product.template'].create({
            'name': 'Test Construction Service',
            'type': 'service',
            'service_tracking': 'task_in_project',
            'service_policy': 'delivered_milestones',
            'construction_template_id': self.construction_template.id,
            'list_price': 10000.0,
        })
        
        # Create test customer
        self.customer = self.env['res.partner'].create({
            'name': 'Test Construction Customer',
            'is_company': True,
            'customer_rank': 1,
        })
    
    def test_construction_template_creation(self):
        """Test construction template creation and basic functionality"""
        self.assertTrue(self.construction_template.id)
        self.assertEqual(self.construction_template.state, 'approved')
        self.assertEqual(len(self.construction_template.task_template_ids), 2)
        self.assertEqual(len(self.construction_template.boq_template_ids), 1)
    
    def test_task_template_hierarchy(self):
        """Test task template parent-child relationships"""
        self.assertEqual(self.task_template_child.parent_template_id, self.task_template_parent)
        self.assertIn(self.task_template_child, self.task_template_parent.child_template_ids)
    
    def test_task_template_validation(self):
        """Test task template validation constraints"""
        # Create another template
        other_template = self.env['construction.project.template'].create({
            'name': 'Other Template',
            'construction_category': 'civil',
        })
        
        # Try to create task with parent from different template - should fail
        with self.assertRaises(ValidationError):
            self.env['construction.task.template'].create({
                'name': 'Invalid Task',
                'template_id': other_template.id,
                'parent_template_id': self.task_template_parent.id,
            })
    
    def test_boq_template_cost_calculation(self):
        """Test BOQ template cost calculations"""
        self.assertEqual(self.boq_template.total_cost, 15000.0)  # 100 * 150
        
        # Update quantity and verify recalculation
        self.boq_template.quantity = 200.0
        self.assertEqual(self.boq_template.total_cost, 30000.0)  # 200 * 150
    
    def test_cost_code_integration(self):
        """Test cost code integration with templates"""
        self.assertEqual(self.task_template_parent.cost_code_id, self.cost_code_material)
        self.assertEqual(self.task_template_child.cost_code_id, self.cost_code_labour)
        self.assertEqual(self.boq_template.cost_code_id, self.cost_code_material)
    
    def test_product_template_integration(self):
        """Test product template integration with construction templates"""
        self.assertEqual(self.service_product.construction_template_id, self.construction_template)
        self.assertEqual(self.service_product.service_tracking, 'task_in_project')
    
    def test_project_creation_from_template(self):
        """Test project creation using construction template"""
        project = self.construction_template.create_construction_project({
            'name': 'Test Construction Project',
            'partner_id': self.customer.id,
        })
        
        self.assertTrue(project.id)
        self.assertTrue(project.is_construction)
        self.assertEqual(project.construction_template_id, self.construction_template)
        
        # Check that tasks were created from templates
        boq_tasks = project.tasks.filtered('is_boq_item')
        self.assertTrue(len(boq_tasks) >= 2)  # At least the template tasks
        
        # Check task hierarchy
        parent_task = boq_tasks.filtered(lambda t: t.boq_code == 'FOUND-001')
        child_task = boq_tasks.filtered(lambda t: t.boq_code == 'FOUND-002')
        
        self.assertTrue(parent_task)
        self.assertTrue(child_task)
        self.assertEqual(child_task.parent_id, parent_task)
    
    def test_sale_order_integration(self):
        """Test sale order integration with construction templates"""
        # Create sale order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
        })
        
        # Create sale order line with construction service
        sale_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.service_product.product_variant_id.id,
            'product_uom_qty': 1.0,
            'price_unit': 10000.0,
        })
        
        # Confirm sale order to trigger project creation
        sale_order.action_confirm()
        
        # Check that project was created with construction template
        self.assertTrue(sale_line.project_id)
        self.assertTrue(sale_line.project_id.is_construction)
        self.assertEqual(sale_line.project_id.construction_template_id, self.construction_template)
    
    def test_cost_code_name_search(self):
        """Test cost code name search functionality"""
        # Search by code
        codes = self.env['construction.cost.code'].name_search('TEST-MAT')
        self.assertTrue(any(code[0] == self.cost_code_material.id for code in codes))
        
        # Search by name
        codes = self.env['construction.cost.code'].name_search('Materials')
        self.assertTrue(any(code[0] == self.cost_code_material.id for code in codes))
    
    def test_template_usage_statistics(self):
        """Test template usage statistics"""
        initial_count = self.construction_template.usage_count
        
        # Create project from template
        project = self.construction_template.create_construction_project({
            'name': 'Usage Test Project',
        })
        
        # Refresh and check usage count increased
        self.construction_template.invalidate_recordset()
        self.assertEqual(self.construction_template.usage_count, initial_count + 1)
        self.assertTrue(self.construction_template.last_used_date)