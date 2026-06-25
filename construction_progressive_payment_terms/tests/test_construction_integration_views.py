# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class TestConstructionIntegrationViews(TransactionCase):
    """Test construction integration views and field handling"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test data
        cls.project = cls.env['project.project'].create({
            'name': 'Test Construction Project',
        })
        
        # Create task without payment milestone
        cls.task_without_milestone = cls.env['project.task'].create({
            'name': 'Task Without Milestone',
            'project_id': cls.project.id,
            'is_boq_item': True,
        })
        
        # Create sale order for milestone testing
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Construction Client',
        })
        
        cls.product = cls.env['product.product'].create({
            'name': 'Construction Service',
            'type': 'service',
            'list_price': 1000.0,
        })
        
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': 1,
                'price_unit': 1000.0,
            })],
        })
        
        # Create payment milestone
        cls.payment_milestone = cls.env['sale.order.payment.milestone'].create({
            'sale_order_id': cls.sale_order.id,
            'milestone_name': 'Test Milestone',
            'percentage': 50.0,
            'amount': 500.0,
            'state': 'draft',
        })
        
        # Create task with payment milestone
        cls.task_with_milestone = cls.env['project.task'].create({
            'name': 'Task With Milestone',
            'project_id': cls.project.id,
            'is_boq_item': True,
            'payment_milestone_id': cls.payment_milestone.id,
        })
    
    def test_milestone_fields_without_milestone(self):
        """Test that milestone fields handle null values gracefully"""
        task = self.task_without_milestone
        
        # Compute milestone fields
        task._compute_milestone_fields()
        task._compute_milestone_progress()
        
        # Should handle null milestone gracefully
        self.assertFalse(task.milestone_state)
        self.assertEqual(task.milestone_amount, 0.0)
        self.assertEqual(task.milestone_percentage, 0.0)
        self.assertEqual(task.milestone_progress, 0.0)
    
    def test_milestone_fields_with_milestone(self):
        """Test that milestone fields compute correctly with valid milestone"""
        task = self.task_with_milestone
        
        # Compute milestone fields
        task._compute_milestone_fields()
        task._compute_milestone_progress()
        
        # Should compute fields correctly
        self.assertEqual(task.milestone_state, 'draft')
        self.assertEqual(task.milestone_amount, 500.0)
        self.assertEqual(task.milestone_percentage, 50.0)
        self.assertEqual(task.milestone_progress, 0.0)  # Draft state = 0% progress
    
    def test_milestone_state_cancelled(self):
        """Test that cancelled state is handled correctly"""
        # Set milestone to cancelled
        self.payment_milestone.state = 'cancelled'
        
        task = self.task_with_milestone
        task._compute_milestone_fields()
        task._compute_milestone_progress()
        
        # Should handle cancelled state
        self.assertEqual(task.milestone_state, 'cancelled')
        self.assertEqual(task.milestone_progress, 0.0)  # Cancelled state = 0% progress
    
    def test_milestone_state_transitions(self):
        """Test all milestone state transitions"""
        states_progress = {
            'draft': 0.0,
            'ready': 25.0,
            'invoiced': 75.0,
            'paid': 100.0,
            'cancelled': 0.0,
        }
        
        task = self.task_with_milestone
        
        for state, expected_progress in states_progress.items():
            with self.subTest(state=state):
                # Set milestone state
                self.payment_milestone.state = state
                
                # Compute fields
                task._compute_milestone_fields()
                task._compute_milestone_progress()
                
                # Check results
                self.assertEqual(task.milestone_state, state)
                self.assertEqual(task.milestone_progress, expected_progress)
    
    def test_view_action_without_milestone(self):
        """Test that view action fails gracefully for task without milestone"""
        task = self.task_without_milestone
        
        with self.assertRaises(ValidationError):
            task.action_view_payment_milestone()
    
    def test_view_action_with_milestone(self):
        """Test that view action works correctly for task with milestone"""
        task = self.task_with_milestone
        
        action = task.action_view_payment_milestone()
        
        # Should return correct action
        self.assertEqual(action['res_model'], 'sale.order.payment.milestone')
        self.assertEqual(action['res_id'], self.payment_milestone.id)
        self.assertEqual(action['view_mode'], 'form')
    
    def test_milestone_progress_update(self):
        """Test milestone progress update from task completion"""
        task = self.task_with_milestone
        
        # Set task to completed stage (mock)
        # Note: This would require setting up proper stages in a real scenario
        task.progress = 100.0
        
        # Update milestone progress
        task.action_update_milestone_progress()
        
        # Check if milestone was updated (if the milestone has task_progress field)
        if hasattr(self.payment_milestone, 'task_progress'):
            self.assertEqual(self.payment_milestone.task_progress, 100.0)
    
    def test_robust_field_access(self):
        """Test that field access is robust against missing attributes"""
        # Create a task with milestone that might have missing attributes
        task = self.task_with_milestone
        
        # Mock missing attributes by temporarily removing them
        original_state = self.payment_milestone.state
        
        try:
            # Test with None values
            self.payment_milestone.state = None
            
            # Should not raise exception
            task._compute_milestone_fields()
            task._compute_milestone_progress()
            
            # Should use fallback values
            self.assertFalse(task.milestone_state or task.milestone_state == 'draft')
            
        finally:
            # Restore original state
            self.payment_milestone.state = original_state
    
    def test_kanban_view_field_loading(self):
        """Test that kanban view fields are properly loaded"""
        # Get task data as would be loaded in kanban view
        tasks = self.env['project.task'].search_read(
            [('id', 'in', [self.task_without_milestone.id, self.task_with_milestone.id])],
            ['payment_milestone_id', 'milestone_state', 'milestone_progress', 'milestone_percentage']
        )
        
        # Should not raise errors when accessing fields
        for task_data in tasks:
            # These fields should be present even if False/0
            self.assertIn('payment_milestone_id', task_data)
            self.assertIn('milestone_state', task_data)
            self.assertIn('milestone_progress', task_data)
            self.assertIn('milestone_percentage', task_data)
    
    def test_tree_view_field_loading(self):
        """Test that tree view fields are properly loaded"""
        # Get task data as would be loaded in tree view
        tasks = self.env['project.task'].search_read(
            [('id', 'in', [self.task_without_milestone.id, self.task_with_milestone.id])],
            ['payment_milestone_id', 'milestone_state', 'milestone_progress', 'milestone_amount', 'is_boq_item']
        )
        
        # Should not raise errors when accessing fields
        for task_data in tasks:
            # These fields should be present even if False/0
            self.assertIn('payment_milestone_id', task_data)
            self.assertIn('milestone_state', task_data)
            self.assertIn('milestone_progress', task_data)
            self.assertIn('milestone_amount', task_data)
            self.assertIn('is_boq_item', task_data)