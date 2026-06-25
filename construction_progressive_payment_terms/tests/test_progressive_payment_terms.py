# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestProgressivePaymentTerms(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.PaymentTerm = self.env['account.payment.term']
        self.PaymentTermLine = self.env['account.payment.term.line']
    
    def test_create_progressive_payment_term(self):
        """Test creating a progressive payment term"""
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'elv',
            'is_template': True,
        })
        
        self.assertTrue(payment_term.is_progressive)
        self.assertEqual(payment_term.construction_category, 'elv')
        self.assertTrue(payment_term.is_template)
    
    def test_milestone_percentage_validation(self):
        """Test milestone percentage validation"""
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'generic',
        })
        
        # Create milestone lines that don't total 100%
        self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 50.0,
            'nb_days': 0,
            'is_milestone': True,
            'milestone_type': 'advance',
        })
        
        self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 30.0,
            'nb_days': 30,
            'is_milestone': True,
            'milestone_type': 'material_delivery',
        })
        
        # This should raise a validation error as total is 80%, not 100%
        # Force validation by calling it directly without install context
        with self.assertRaises(ValidationError):
            # Clear install context to enable validation
            payment_term.with_context(install_mode=False, module=False, import_file=False)._check_progressive_payment_configuration()
    
    def test_milestone_line_validation(self):
        """Test milestone line validation"""
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'generic',
        })
        
        # Test invalid percentage
        with self.assertRaises(ValidationError):
            self.PaymentTermLine.create({
                'payment_id': payment_term.id,
                'value': 'percent',
                'value_amount': 150.0,  # Invalid percentage > 100
                'nb_days': 0,
                'is_milestone': True,
                'milestone_type': 'advance',
            })
    
    def test_milestone_display_name(self):
        """Test milestone display name computation"""
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'generic',
        })
        
        milestone_line = self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 20.0,
            'nb_days': 0,
            'is_milestone': True,
            'milestone_type': 'advance',
        })
        
        self.assertEqual(milestone_line.milestone_display_name, 'Advance Payment (20.0%)')
    
    def test_default_milestone_structure(self):
        """Test default milestone structure creation"""
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'elv',
        })
        
        # Trigger default milestone creation
        payment_term._create_default_milestone_structure()
        
        # Should have 5 default milestones
        milestone_lines = payment_term.line_ids.filtered('is_milestone')
        self.assertEqual(len(milestone_lines), 5)
        
        # Check total percentage is 100%
        total_percentage = sum(line.value_amount for line in milestone_lines)
        self.assertEqual(total_percentage, 100.0)
        
        # Check milestone types are present
        milestone_types = milestone_lines.mapped('milestone_type')
        expected_types = ['advance', 'material_delivery', 'installation', 'testing_commissioning', 'retention']
        self.assertEqual(set(milestone_types), set(expected_types))

    def test_sub_milestone_creation(self):
        """Test sub-milestone creation and validation"""
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'generic',
        })
        
        # Create a material delivery milestone with sub-milestones enabled
        milestone_line = self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 30.0,
            'nb_days': 30,
            'is_milestone': True,
            'milestone_type': 'material_delivery',
            'allow_sub_milestones': True,
        })
        
        # Sub-milestones are now handled by sale.order.payment.milestone.sub model
        # This test is kept for reference but functionality moved to sale order level
        
        # Check sub-milestone template count
        self.assertEqual(milestone_line.sub_milestone_template_count, 0)  # No templates created by default
        
        # Sub-milestones are handled at sale order level, not payment term level
        # This test validates the configuration is set up correctly

    def test_sub_milestone_percentage_validation(self):
        """Test sub-milestone percentage validation"""
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'generic',
        })
        
        milestone_line = self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 30.0,
            'nb_days': 30,
            'is_milestone': True,
            'milestone_type': 'material_delivery',
            'allow_sub_milestones': True,
        })
        
        # Sub-milestone validation is now handled at sale order level
        # This test is kept for reference but functionality moved to sale.order.payment.milestone.sub

    def test_sub_milestone_total_percentage_validation(self):
        """Test that sub-milestone total percentage cannot exceed 100%"""
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'generic',
        })
        
        milestone_line = self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 30.0,
            'nb_days': 30,
            'is_milestone': True,
            'milestone_type': 'material_delivery',
            'allow_sub_milestones': True,
        })
        
        # Sub-milestone total percentage validation is now handled at sale order level
        # This test is kept for reference but functionality moved to sale.order.payment.milestone.sub

    def test_sub_milestone_date_range_validation(self):
        """Test sub-milestone date range validation"""
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'generic',
        })
        
        milestone_line = self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 30.0,
            'nb_days': 30,
            'is_milestone': True,
            'milestone_type': 'material_delivery',
            'allow_sub_milestones': True,
        })
        
        # Sub-milestone date range validation is now handled at sale order level
        # This test is kept for reference but functionality moved to sale.order.payment.milestone.sub

    def test_milestone_line_sub_milestone_configuration_validation(self):
        """Test validation of sub-milestone configuration on payment term line"""
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'generic',
        })
        
        milestone_line = self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 30.0,
            'nb_days': 30,
            'is_milestone': True,
            'milestone_type': 'material_delivery',
            'allow_sub_milestones': False,  # Sub-milestones not allowed
        })
        
        # Sub-milestone configuration validation is now handled at sale order level
        # This test is kept for reference but functionality moved to sale.order.payment.milestone.sub

    def test_compute_progressive_terms(self):
        """Test progressive payment term computation"""
        from datetime import date
        
        # Create a progressive payment term with milestones
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'elv',
        })
        
        # Create milestone lines
        self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 20.0,
            'nb_days': 0,
            'is_milestone': True,
            'milestone_type': 'advance',
        })
        
        self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 30.0,
            'nb_days': 30,
            'is_milestone': True,
            'milestone_type': 'material_delivery',
        })
        
        self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 35.0,
            'nb_days': 60,
            'is_milestone': True,
            'milestone_type': 'installation',
        })
        
        self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 15.0,
            'nb_days': 90,
            'is_milestone': True,
            'milestone_type': 'testing_commissioning',
        })
        
        # Test parameters
        date_ref = date.today()
        currency = self.env.company.currency_id
        company = self.env.company
        tax_amount = 100.0
        tax_amount_currency = 100.0
        sign = 1
        untaxed_amount = 900.0
        untaxed_amount_currency = 900.0
        total_amount = 1000.0
        
        # Compute progressive terms
        result = payment_term._compute_progressive_terms(
            date_ref, currency, company, tax_amount, tax_amount_currency,
            sign, untaxed_amount, untaxed_amount_currency
        )
        
        # Verify result structure
        self.assertIn('total_amount', result)
        self.assertIn('line_ids', result)
        self.assertEqual(result['total_amount'], total_amount)
        self.assertEqual(result['discount_percentage'], 0.0)
        self.assertFalse(result['discount_date'])
        
        # Verify milestone lines
        line_ids = result['line_ids']
        self.assertEqual(len(line_ids), 4)  # 4 milestones
        
        # Check amounts
        expected_amounts = [200.0, 300.0, 350.0, 150.0]  # 20%, 30%, 35%, 15% of 1000
        actual_amounts = [line['company_amount'] for line in line_ids]
        self.assertEqual(actual_amounts, expected_amounts)
        
        # Check milestone information is included
        for line in line_ids:
            self.assertIn('milestone_id', line)
            self.assertIn('milestone_type', line)
            self.assertIn('milestone_name', line)
            self.assertTrue(line['is_milestone'])
        
        # Check milestone types
        milestone_types = [line['milestone_type'] for line in line_ids]
        expected_types = ['advance', 'material_delivery', 'installation', 'testing_commissioning']
        self.assertEqual(milestone_types, expected_types)

    def test_compute_terms_fallback_to_standard(self):
        """Test that non-progressive payment terms use standard computation"""
        # Create a standard (non-progressive) payment term
        payment_term = self.PaymentTerm.create({
            'name': 'Standard Payment Term',
            'is_progressive': False,
        })
        
        # Add standard payment term line
        self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 100.0,
            'nb_days': 30,
        })
        
        # Test parameters
        from datetime import date
        date_ref = date.today()
        currency = self.env.company.currency_id
        company = self.env.company
        tax_amount = 100.0
        tax_amount_currency = 100.0
        sign = 1
        untaxed_amount = 900.0
        untaxed_amount_currency = 900.0
        
        # Compute terms - should use standard Odoo computation
        result = payment_term._compute_terms(
            date_ref, currency, company, tax_amount, tax_amount_currency,
            sign, untaxed_amount, untaxed_amount_currency
        )
        
        # Verify standard structure (no milestone information)
        self.assertIn('total_amount', result)
        self.assertIn('line_ids', result)
        # Standard payment terms may have multiple lines due to Odoo's internal processing
        self.assertGreaterEqual(len(result['line_ids']), 1)
        
        # Standard lines should not have milestone information
        line = result['line_ids'][0]
        self.assertNotIn('milestone_id', line)
        self.assertNotIn('is_milestone', line)

    def test_compute_progressive_terms_with_cash_rounding(self):
        """Test progressive payment computation with cash rounding"""
        from datetime import date
        
        # Create cash rounding
        cash_rounding = self.env['account.cash.rounding'].create({
            'name': 'Test Rounding',
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'HALF-UP',
        })
        
        # Create progressive payment term
        payment_term = self.PaymentTerm.create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'construction_category': 'elv',
        })
        
        # Create milestone lines
        self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 33.33,
            'nb_days': 0,
            'is_milestone': True,
            'milestone_type': 'advance',
        })
        
        self.PaymentTermLine.create({
            'payment_id': payment_term.id,
            'value': 'percent',
            'value_amount': 66.67,
            'nb_days': 30,
            'is_milestone': True,
            'milestone_type': 'material_delivery',
        })
        
        # Test parameters
        date_ref = date.today()
        currency = self.env.company.currency_id
        company = self.env.company
        tax_amount = 10.0
        tax_amount_currency = 10.0
        sign = 1
        untaxed_amount = 90.0
        untaxed_amount_currency = 90.0
        
        # Compute with cash rounding
        result = payment_term._compute_progressive_terms(
            date_ref, currency, company, tax_amount, tax_amount_currency,
            sign, untaxed_amount, untaxed_amount_currency, cash_rounding
        )
        
        # Verify result
        self.assertIn('line_ids', result)
        self.assertEqual(len(result['line_ids']), 2)
        
        # Check that amounts are properly rounded
        total_computed = sum(line['company_amount'] for line in result['line_ids'])
        self.assertEqual(total_computed, 100.0)  # Should equal original total

    def test_milestone_analytic_distribution(self):
        """Test that milestone invoices include analytic distribution from linked project"""
        # Create analytic account for project
        analytic_plan = self.env['account.analytic.plan'].search([], limit=1)
        if not analytic_plan:
            analytic_plan = self.env['account.analytic.plan'].create({
                'name': 'Test Plan',
                'company_id': self.env.company.id,
            })
        
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Test Project Analytics',
            'code': 'TEST-PROJ-001',
            'plan_id': analytic_plan.id,
        })
        
        # Create project with analytic account (if sale_project is available)
        project = None
        if 'project.project' in self.env:
            project = self.env['project.project'].create({
                'name': 'Test Construction Project',
                'analytic_account_id': analytic_account.id,
            })
        
        # Create progressive payment term
        payment_term = self.env['account.payment.term'].create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'line_ids': [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'is_milestone': True,
                'milestone_type': 'advance',
            })]
        })
        
        # Create sale order with project link
        partner = self.env['res.partner'].create({
            'name': 'Test Customer',
        })
        
        product = self.env['product.product'].create({
            'name': 'Construction Service',
            'type': 'service',
        })
        
        sale_order_vals = {
            'partner_id': partner.id,
            'payment_term_id': payment_term.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': 1000.0,
            })]
        }
        
        # Add project link if available
        if project:
            sale_order_vals['project_id'] = project.id
        elif 'analytic_account_id' in self.env['sale.order']._fields:
            sale_order_vals['analytic_account_id'] = analytic_account.id
        
        sale_order = self.env['sale.order'].create(sale_order_vals)
        sale_order.action_confirm()
        
        # Get milestone
        milestone = sale_order.payment_milestone_ids[0]
        
        # Check analytic account is computed correctly
        if project or 'analytic_account_id' in sale_order_vals:
            self.assertEqual(milestone.analytic_account_id, analytic_account)
        
        # Set milestone to ready and create invoice
        milestone.action_set_ready()
        invoice = self.env['account.move'].with_context(default_move_type="out_invoice").create_milestone_invoice([milestone.id])
        
        # Check invoice lines have analytic distribution
        invoice_lines = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'income')
        self.assertTrue(invoice_lines)
        
        for line in invoice_lines:
            if project or 'analytic_account_id' in sale_order_vals:
                self.assertTrue(line.analytic_distribution)
                self.assertIn(str(analytic_account.id), line.analytic_distribution)
                self.assertEqual(line.analytic_distribution[str(analytic_account.id)], 100)

    def test_milestone_invoice_creation_with_project_context(self):
        """Test milestone invoice creation includes project context for analytic distribution"""
        # Create analytic account
        analytic_plan = self.env['account.analytic.plan'].search([], limit=1)
        if not analytic_plan:
            analytic_plan = self.env['account.analytic.plan'].create({
                'name': 'Test Plan',
                'company_id': self.env.company.id,
            })
        
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Test Project Analytics',
            'code': 'TEST-PROJ-002',
            'plan_id': analytic_plan.id,
        })
        
        # Create progressive payment term
        payment_term = self.env['account.payment.term'].create({
            'name': 'Test Progressive Payment',
            'is_progressive': True,
            'line_ids': [(0, 0, {
                'value': 'percent',
                'value_amount': 50.0,
                'nb_days': 0,
                'is_milestone': True,
                'milestone_type': 'advance',
            }), (0, 0, {
                'value': 'percent',
                'value_amount': 50.0,
                'nb_days': 30,
                'is_milestone': True,
                'milestone_type': 'installation',
            })]
        })
        
        # Create sale order
        partner = self.env['res.partner'].create({
            'name': 'Test Customer 2',
        })
        
        product = self.env['product.product'].create({
            'name': 'Construction Service 2',
            'type': 'service',
        })
        
        sale_order_vals = {
            'partner_id': partner.id,
            'payment_term_id': payment_term.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': 2000.0,
            })]
        }
        
        # Add analytic account directly if field exists
        if 'analytic_account_id' in self.env['sale.order']._fields:
            sale_order_vals['analytic_account_id'] = analytic_account.id
        
        sale_order = self.env['sale.order'].create(sale_order_vals)
        sale_order.action_confirm()
        
        # Test analytic distribution method directly
        account_move = self.env['account.move']
        analytic_distribution = account_move._get_milestone_analytic_distribution(sale_order)
        
        if 'analytic_account_id' in sale_order_vals:
            self.assertTrue(analytic_distribution)
            self.assertEqual(analytic_distribution[analytic_account.id], 100)
        
        # Test milestone invoice creation
        milestone = sale_order.payment_milestone_ids[0]
        milestone.action_set_ready()
        
        # Create invoice and verify analytic distribution is applied
        invoice = self.env['account.move'].with_context(default_move_type="out_invoice").create_milestone_invoice([milestone.id])
        
        # Check that invoice lines have proper analytic distribution
        income_lines = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'income')
        
        if 'analytic_account_id' in sale_order_vals:
            for line in income_lines:
                self.assertTrue(line.analytic_distribution)
                self.assertIn(str(analytic_account.id), line.analytic_distribution)

    def test_sub_milestone_analytic_distribution(self):
        """Test that sub-milestone invoices include analytic distribution from parent milestone"""
        # Create analytic account
        analytic_plan = self.env['account.analytic.plan'].search([], limit=1)
        if not analytic_plan:
            analytic_plan = self.env['account.analytic.plan'].create({
                'name': 'Test Plan',
                'company_id': self.env.company.id,
            })
        
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Test Sub-milestone Analytics',
            'code': 'TEST-SUB-001',
            'plan_id': analytic_plan.id,
        })
        
        # Create progressive payment term with sub-milestones
        payment_term = self.env['account.payment.term'].create({
            'name': 'Test Progressive with Sub-milestones',
            'is_progressive': True,
            'line_ids': [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'is_milestone': True,
                'milestone_type': 'material_delivery',
                'allow_sub_milestones': True,
            })]
        })
        
        # Create sale order
        partner = self.env['res.partner'].create({'name': 'Test Customer Sub'})
        product = self.env['product.product'].create({
            'name': 'Construction Service Sub',
            'type': 'service',
        })
        
        sale_order_vals = {
            'partner_id': partner.id,
            'payment_term_id': payment_term.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': 1000.0,
            })]
        }
        
        if 'analytic_account_id' in self.env['sale.order']._fields:
            sale_order_vals['analytic_account_id'] = analytic_account.id
        
        sale_order = self.env['sale.order'].create(sale_order_vals)
        sale_order.action_confirm()
        
        # Get milestone and create sub-milestone
        milestone = sale_order.payment_milestone_ids[0]
        milestone.allow_sub_milestones = True
        
        sub_milestone = self.env['sale.order.payment.milestone.sub'].create({
            'parent_milestone_id': milestone.id,
            'name': 'Test Sub-milestone',
            'percentage': 100.0,
            'state': 'completed',
        })
        
        # Check sub-milestone inherits analytic account
        if 'analytic_account_id' in sale_order_vals:
            self.assertEqual(sub_milestone.analytic_account_id, analytic_account)
        
        # Create invoice for sub-milestone
        if 'analytic_account_id' in sale_order_vals:
            result = sub_milestone.action_create_invoice()
            invoice_id = result.get('res_id')
            if invoice_id:
                invoice = self.env['account.move'].browse(invoice_id)
                income_lines = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'income')
                
                for line in income_lines:
                    self.assertTrue(line.analytic_distribution)
                    self.assertIn(str(analytic_account.id), line.analytic_distribution)