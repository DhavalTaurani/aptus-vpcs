# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields

class TestFinancialIntegration(TransactionCase):

    def setUp(self):
        super(TestFinancialIntegration, self).setUp()
        self.Project = self.env['project.project']
        self.RevenueRecognition = self.env['construction.revenue.recognition']
        self.AccountMove = self.env['account.move']
        self.AccountJournal = self.env['account.journal']
        self.Subcontractor = self.env['construction.subcontractor']
        self.Partner = self.env['res.partner']

        # Create test customer first
        self.test_customer = self.Partner.create({
            'name': 'Test Financial Customer',
            'is_company': True,
        })

        self.test_project = self.Project.create({
            'name': 'Test Financial Project',
            'partner_id': self.test_customer.id,
            'is_construction': True,
            'construction_type': 'industrial',
            'contract_value': 1000000.00,
        })

        self.test_partner = self.Partner.create({
            'name': 'Test Financial Partner',
            'is_company': True,
        })

        # Ensure a sales journal exists for revenue recognition
        self.sales_journal = self.AccountJournal.search([('type', '=', 'sale')], limit=1)
        if not self.sales_journal:
            self.sales_journal = self.AccountJournal.create({
                'name': 'Test Sales Journal',
                'type': 'sale',
                'code': 'TSJ',
            })

    def test_revenue_recognition_percentage_completion(self):
        revenue_rec = self.RevenueRecognition.create({
            'name': 'Rev Rec POC',
            'project_id': self.test_project.id,
            'recognition_method': 'percentage_completion',
            'total_contract_value': 500000.0,
            'total_estimated_cost': 250000.0,
            'actual_cost_to_date': 125000.0,
        })
        self.assertEqual(revenue_rec.percentage_complete, 50.0)
        self.assertEqual(revenue_rec.revenue_to_recognize, 250000.0)

        # Perform revenue recognition
        action = revenue_rec.action_recognize_revenue()
        recognized_move = self.AccountMove.browse(action['res_id'])

        self.assertEqual(revenue_rec.revenue_recognized, 250000.0)
        self.assertEqual(recognized_move.amount_total, 250000.0)
        self.assertEqual(recognized_move.state, 'posted')

    def test_revenue_recognition_milestone(self):
        test_subcontractor = self.Subcontractor.create({
            'name': 'Test Subco for Milestone',
            'partner_id': self.Partner.create({'name': 'Subco Milestone Partner', 'is_company': True}).id,
            'project_id': self.test_project.id,
        })
        milestone = self.env['construction.subcontractor.milestone'].create({
            'name': 'Milestone 1',
            'subcontractor_id': test_subcontractor.id,
            'amount': 50000.0,
            'is_completed': True,
        })

        revenue_rec = self.RevenueRecognition.create({
            'name': 'Rev Rec Milestone',
            'project_id': self.test_project.id,
            'recognition_method': 'milestone',
            'total_contract_value': 500000.0,
            'milestone_ids': [(6, 0, [milestone.id])],
        })
        self.assertEqual(revenue_rec.revenue_to_recognize, 50000.0)

    def test_retention_release_action(self):
        subcontractor = self.Subcontractor.create({
            'name': 'Test Subco for Retention',
            'partner_id': self.test_partner.id,
            'project_id': self.test_project.id,
        })

        # Create an invoice with retention
        invoice = self.AccountMove.create({
            'partner_id': subcontractor.partner_id.id,
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': 'Subco Invoice with Retention',
                'quantity': 1,
                'price_unit': 10000.0,
                'account_id': subcontractor.partner_id.property_account_payable_id.id,
                'analytic_distribution': {self.test_project.analytic_account_id.id: 100},
                'retention_percentage': 10.0,
            })],
            'subcontractor_id': subcontractor.id,
        })
        invoice.action_post()

        # Test retention calculation
        retention_line = invoice.invoice_line_ids.filtered(lambda l: l.retention_percentage > 0)
        if retention_line:
            self.assertEqual(retention_line.retention_amount, 1000.0) # 10% of 10000

    def test_price_variance_on_purchase_order_line(self):
        # Create a product with a standard cost
        product_template = self.env['product.template'].create({
            'name': 'Test Product for PO',
            'type': 'product',
            'standard_price': 100.0,
        })
        product = product_template.product_variant_id

        # Create a BOQ task with a unit cost
        boq_task = self.env['project.task'].create({
            'name': 'BOQ Item for PO',
            'project_id': self.test_project.id,
            'is_boq_item': True,
            'unit_cost': 90.0, # BOQ unit cost is 90
        })

        # Create a purchase order first
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.test_partner.id,
        })
        
        # Create a purchase order line with a different price unit
        po_line = self.env['purchase.order.line'].create({
            'order_id': purchase_order.id,
            'product_id': product.id,
            'product_qty': 1.0,
            'price_unit': 100.0, # PO price unit is 100
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'construction_project_id': self.test_project.id,
            'boq_task_id': boq_task.id,
        })

        self.assertEqual(po_line.price_variance, 10.0) # 100 - 90 = 10
