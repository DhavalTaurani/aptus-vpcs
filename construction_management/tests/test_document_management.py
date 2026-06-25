# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase

class TestDocumentManagement(TransactionCase):

    def setUp(self):
        super(TestDocumentManagement, self).setUp()
        self.Project = self.env['project.project']
        self.DocumentDirectory = self.env['construction.document.directory']
        self.Submittal = self.env['construction.submittal']
        self.Attachment = self.env['ir.attachment']

        self.test_project = self.Project.create({
            'name': 'Test Document Project',
            'is_construction': True,
            'construction_type': 'commercial',
        })

    def test_default_directories_creation(self):
        # Default directories should be created automatically on project creation
        self.assertTrue(self.test_project.document_directory_ids)
        self.assertEqual(len(self.test_project.document_directory_ids), 8)

    def test_document_upload_wizard(self):
        doc_dir = self.DocumentDirectory.create({
            'name': 'Test Upload Dir',
            'project_id': self.test_project.id,
            'document_type': 'other',
        })
        self.assertEqual(doc_dir.document_count, 0)

        attachment = self.Attachment.create({
            'name': 'test_file.txt',
            'datas': 'SGVsbG8gV29ybGQ=',
            'mimetype': 'text/plain',
        })

        upload_wizard = self.env['construction.upload.document'].create({
            'project_id': self.test_project.id,
            'directory_id': doc_dir.id,
            'attachment_ids': [(6, 0, [attachment.id])],
        })
        upload_wizard.upload_document()

        # Trigger recomputation of document count
        doc_dir._compute_document_count()
        self.assertEqual(doc_dir.document_count, 1)
        self.assertEqual(attachment.res_model, 'construction.document.directory')
        self.assertEqual(attachment.res_id, doc_dir.id)

    def test_submittal_workflow(self):
        submittal = self.Submittal.create({
            'name': 'SUB001',
            'project_id': self.test_project.id,
            'submittal_type': 'shop_drawings',
        })
        self.assertEqual(submittal.state, 'draft')

        submittal.action_submit()
        self.assertEqual(submittal.state, 'submitted')

        submittal.action_send_for_review()
        self.assertEqual(submittal.state, 'under_review')

        submittal.action_approve()
        self.assertEqual(submittal.state, 'approved')
        self.assertTrue(submittal.approval_date)

        # Test rejection and resubmit
        submittal_2 = self.Submittal.create({
            'name': 'SUB002',
            'project_id': self.test_project.id,
            'submittal_type': 'product_data',
        })
        submittal_2.action_submit()
        submittal_2.action_send_for_review()
        submittal_2.action_reject()
        self.assertEqual(submittal_2.state, 'rejected')

        submittal_2.action_resubmit()
        self.assertEqual(submittal_2.state, 'resubmit')
