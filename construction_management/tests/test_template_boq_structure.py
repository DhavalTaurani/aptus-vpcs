# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestTemplateBOQStructure(TransactionCase):
    """Test template-based BOQ structure with task hierarchy"""

    def setUp(self):
        super().setUp()
        
        # Create test cost codes
        self.cost_code_material = self.env['construction.cost.code'].create({
            'name': 'Test Materials',
            'code': 'TEST-MAT',
            'cost_type': 'material',
            'standard_cost': 100.0,
        })
        
        self.cost_code_labour = self.env['construction.cost.code'].create({
            'name': 'Test Labour',
            'code': 'TEST-LAB',
            'cost_type': 'labour',
            'standard_cost': 200.0,
        })
        
        # Create test project template
        self.template = self.env['construction.project.template'].create({
            'name': 'Test Construction Template',
            'construction_category': 'general',
            'description': 'Test template for BOQ structure',
            'state': 'approved',
            'version': '1.0',
        })

    def test_task_template_hierarchy_creation(self):
        """Test creation of task templates with proper hierarchy"""
        # Create parent task (phase level)
        parent_task = self.env['construction.task.template'].create({
            'name': 'Foundation Phase',
            'template_id': self.template.id,
            'hierarchy_level': 'phase',
            'initial_stage': 'task_stage_draft',
            'sequence': 10,
        })
        
        # Create child task (work package level)
        child_task = self.env['construction.task.template'].create({
            'name': 'Concrete Work',
            'template_id': self.template.id,
            'parent_template_id': parent_task.id,
            'hierarchy_level': 'work_package',
            'initial_stage': 'task_stage_draft',
            'is_boq_item': True,
            'boq_code': 'TEST-CONC-001',
            'estimated_quantity': 100.0,
            'unit_cost': 150.0,
            'cost_code_id': self.cost_code_material.id,
            'sequence': 20,
        })
        
        self.assertEqual(child_task.parent_template_id, parent_task)
        self.assertEqual(parent_task.child_template_ids[0], child_task)
        self.assertTrue(child_task.is_boq_item)
        self.assertEqual(child_task.boq_code, 'TEST-CONC-001')

    def test_boq_template_creation(self):
        """Test creation of BOQ templates"""
        # Create task template first
        task_template = self.env['construction.task.template'].create({
            'name': 'Structural Work',
            'template_id': self.template.id,
            'hierarchy_level': 'work_package',
            'is_boq_item': True,
        })
        
        # Create BOQ template
        boq_template = self.env['construction.boq.template'].create({
            'name': 'Steel Reinforcement',
            'code': 'TEST-STEEL-001',
            'template_id': self.template.id,
            'task_template_id': task_template.id,
            'quantity': 50.0,
            'unit_of_measure_id': self.env.ref('uom.product_uom_kgm').id,
            'unit_cost': 5.0,
            'cost_code_id': self.cost_code_material.id,
        })
        
        self.assertEqual(boq_template.total_cost, 250.0)  # 50 * 5
        self.assertEqual(boq_template.task_template_id, task_template)

    def test_milestone_template_creation(self):
        """Test creation of milestone templates"""
        milestone_template = self.env['construction.milestone.template'].create({
            'name': 'Foundation Complete',
            'template_id': self.template.id,
            'milestone_type': 'phase_completion',
            'days_from_start': 30,
            'is_payment_milestone': True,
            'payment_percentage': 25.0,
        })
        
        self.assertEqual(milestone_template.milestone_type, 'phase_completion')
        self.assertTrue(milestone_template.is_payment_milestone)
        self.assertEqual(milestone_template.payment_percentage, 25.0)

    def test_resource_allocation_template_creation(self):
        """Test creation of resource allocation templates"""
        # Create task template first
        task_template = self.env['construction.task.template'].create({
            'name': 'Excavation Work',
            'template_id': self.template.id,
            'hierarchy_level': 'work_package',
        })
        
        # Create resource allocation template
        resource_template = self.env['construction.resource.allocation.template'].create({
            'name': 'Excavator Operator',
            'task_template_id': task_template.id,
            'resource_type': 'human',
            'allocated_quantity': 2.0,
            'duration_days': 5.0,
            'unit_cost': 300.0,
        })
        
        self.assertEqual(resource_template.total_cost, 600.0)  # 2 * 300
        self.assertEqual(resource_template.task_template_id, task_template)

    def test_project_creation_from_template(self):
        """Test project creation from template with BOQ structure"""
        # Create complete template structure
        parent_task = self.env['construction.task.template'].create({
            'name': 'Site Preparation',
            'template_id': self.template.id,
            'hierarchy_level': 'phase',
            'initial_stage': 'task_stage_draft',
            'sequence': 10,
        })
        
        child_task = self.env['construction.task.template'].create({
            'name': 'Excavation',
            'template_id': self.template.id,
            'parent_template_id': parent_task.id,
            'hierarchy_level': 'work_package',
            'initial_stage': 'task_stage_draft',
            'is_boq_item': True,
            'boq_code': 'TEST-EXC-001',
            'estimated_quantity': 200.0,
            'unit_cost': 25.0,
            'cost_code_id': self.cost_code_labour.id,
            'sequence': 20,
        })
        
        # Create milestone
        milestone_template = self.env['construction.milestone.template'].create({
            'name': 'Site Preparation Complete',
            'template_id': self.template.id,
            'milestone_type': 'phase_completion',
            'days_from_start': 15,
        })
        
        # Create project from template
        project = self.template.create_construction_project({
            'name': 'Test Construction Project',
            'description': 'Test project from template',
        })
        
        # Verify project creation
        self.assertTrue(project.is_construction)
        self.assertEqual(project.construction_template_id, self.template)
        
        # Verify tasks were created
        phase_task = project.task_ids.filtered(lambda t: t.name == 'Site Preparation')
        work_package_task = project.task_ids.filtered(lambda t: t.name == 'Excavation')
        
        self.assertTrue(phase_task)
        self.assertTrue(work_package_task)
        self.assertEqual(work_package_task.parent_id, phase_task)
        self.assertTrue(work_package_task.is_boq_item)
        self.assertEqual(work_package_task.boq_code, 'TEST-EXC-001')
        
        # Verify milestones were created
        milestone = project.milestone_ids.filtered(lambda m: m.name == 'Site Preparation Complete')
        self.assertTrue(milestone)

    def test_template_customization_wizard(self):
        """Test template customization wizard functionality"""
        # Create task template
        task_template = self.env['construction.task.template'].create({
            'name': 'Foundation Work',
            'template_id': self.template.id,
            'hierarchy_level': 'work_package',
            'is_boq_item': True,
            'estimated_quantity': 100.0,
            'unit_cost': 150.0,
        })
        
        # Create customization wizard
        wizard = self.env['construction.template.customization.wizard'].create({
            'template_id': self.template.id,
            'project_name': 'Customized Test Project',
            'project_description': 'Test customized project',
            'customize_tasks': True,
            'contract_value': 50000.0,
        })
        
        # Trigger onchange to load template data
        wizard._onchange_template_id()
        
        # Verify task customization lines were created
        self.assertTrue(wizard.task_customization_ids)
        task_customization = wizard.task_customization_ids[0]
        self.assertEqual(task_customization.name, 'Foundation Work')
        self.assertEqual(task_customization.estimated_quantity, 100.0)
        
        # Modify customization
        task_customization.write({
            'name': 'Modified Foundation Work',
            'estimated_quantity': 120.0,
            'unit_cost': 160.0,
        })
        
        # Create project with customizations
        action = wizard.action_create_project()
        project_id = action['res_id']
        project = self.env['project.project'].browse(project_id)
        
        # Verify customizations were applied
        self.assertEqual(project.name, 'Customized Test Project')
        self.assertEqual(project.contract_value, 50000.0)
        
        # Find the customized task
        customized_task = project.task_ids.filtered(lambda t: 'Foundation' in t.name)
        self.assertTrue(customized_task)
        self.assertEqual(customized_task.name, 'Modified Foundation Work')
        self.assertEqual(customized_task.estimated_quantity, 120.0)

    def test_sequence_generation(self):
        """Test sequence generation for BOQ codes"""
        # Create task template without BOQ code
        task_template = self.env['construction.task.template'].create({
            'name': 'Test Task',
            'template_id': self.template.id,
            'hierarchy_level': 'work_package',
            'is_boq_item': True,
            'estimated_quantity': 10.0,
            'unit_cost': 100.0,
        })
        
        # Create project from template
        project = self.template.create_construction_project({
            'name': 'Sequence Test Project',
        })
        
        # Find the created task
        created_task = project.task_ids.filtered(lambda t: t.name == 'Test Task')
        self.assertTrue(created_task)
        
        # Verify BOQ code was generated
        self.assertTrue(created_task.boq_code)
        self.assertTrue(created_task.boq_code.startswith('BOQ-'))

    def test_validation_constraints(self):
        """Test validation constraints"""
        # Test positive quantity constraint
        with self.assertRaises(ValidationError):
            self.env['construction.task.template'].create({
                'name': 'Invalid Task',
                'template_id': self.template.id,
                'estimated_quantity': -10.0,  # Negative quantity should fail
                'unit_cost': 100.0,
            })
        
        # Test positive unit cost constraint
        with self.assertRaises(ValidationError):
            self.env['construction.task.template'].create({
                'name': 'Invalid Task',
                'template_id': self.template.id,
                'estimated_quantity': 10.0,
                'unit_cost': -100.0,  # Negative cost should fail
            })