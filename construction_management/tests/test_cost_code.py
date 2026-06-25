# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestCostCode(TransactionCase):

    def setUp(self):
        super(TestCostCode, self).setUp()
        self.CostCode = self.env['construction.cost.code']

    def test_create_cost_code(self):
        cost_code = self.CostCode.create({
            'name': 'Test Cost Code',
            'code': 'CC07082025001',
            'cost_type': 'material',
        })
        self.assertTrue(cost_code)
        self.assertEqual(cost_code.name, 'Test Cost Code')

    def test_unique_cost_code(self):
        # Use a random UUID to ensure uniqueness
        import uuid
        test_code = f'TEST_UNIQUE_{str(uuid.uuid4())[:8]}'
        
        # Create first cost code
        first_code = self.CostCode.create({
            'name': 'Unique Code 1',
            'code': test_code,
            'cost_type': 'labour',
        })
        self.assertTrue(first_code)
        
        # Try to create duplicate - should raise exception due to unique constraint
        with self.assertRaises(Exception):
            self.CostCode.create({
                'name': 'Duplicate Code',
                'code': test_code,
                'cost_type': 'equipment',
            })

    def test_cost_type_selection(self):
        cost_code = self.CostCode.create({
            'name': 'Test Cost Type',
            'code': 'CCT001',
            'cost_type': 'subcontractor',
        })
        self.assertEqual(cost_code.cost_type, 'subcontractor')

    def test_hierarchy(self):
        parent_code = self.CostCode.create({
            'name': 'Parent Code',
            'code': 'PC07082025001',
            'cost_type': 'overhead',
        })
        child_code = self.CostCode.create({
            'name': 'Child Code',
            'code': 'CH07082025001',
            'cost_type': 'overhead',  # Same cost type as parent
            'parent_id': parent_code.id,
        })
        self.assertEqual(child_code.parent_id, parent_code)
        self.assertIn(child_code, parent_code.child_ids)
