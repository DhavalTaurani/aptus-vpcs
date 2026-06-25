# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestTemplateManagement(TransactionCase):
    """Test template data management functionality"""

    def setUp(self):
        super().setUp()
        self.template_model = self.env['construction.project.template']
        self.version_model = self.env['construction.template.version']
        self.analytics_model = self.env['construction.template.analytics']

    def test_template_creation(self):
        """Test basic template creation"""
        template = self.template_model.create({
            'name': 'Test Template',
            'construction_category': 'general',
            'description': 'Test template for validation',
            'version': '1.0',
        })
        self.assertTrue(template.id)
        self.assertEqual(template.state, 'draft')

    def test_template_validation(self):
        """Test template validation constraints"""
        # Test version format validation
        with self.assertRaises(ValidationError):
            self.template_model.create({
                'name': 'Invalid Version Template',
                'construction_category': 'general',
                'version': 'invalid-version',
            })

    def test_template_backup_creation(self):
        """Test template backup functionality"""
        template = self.template_model.create({
            'name': 'Backup Test Template',
            'construction_category': 'elv',
            'description': 'Template for backup testing',
            'version': '1.0',
        })
        
        # Create a backup
        version = template.create_version_backup("Test backup")
        self.assertTrue(version.id)
        self.assertEqual(version.template_id, template)
        self.assertEqual(version.change_log, "Test backup")

    def test_cron_methods(self):
        """Test cron job methods"""
        # Test backup cron
        backup_count = self.template_model._cron_create_template_backups()
        self.assertIsInstance(backup_count, int)
        
        # Test analytics cron
        analytics_count = self.analytics_model._cron_generate_monthly_analytics()
        self.assertIsInstance(analytics_count, int)
        
        # Test cleanup cron
        cleanup_count = self.template_model._cron_cleanup_old_backups()
        self.assertIsInstance(cleanup_count, int)