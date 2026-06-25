# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ConstructionUploadDocument(models.TransientModel):
    _name = "construction.upload.document"
    _description = "Upload Construction Document Wizard"

    project_id = fields.Many2one("project.project", "Project", required=True)
    directory_id = fields.Many2one(
        "construction.document.directory", "Directory", required=True
    )
    document_type = fields.Selection(selection=[("construction", "Construction"), ("project", "Project")], default="construction", string="Document Type")
    attachment_ids = fields.Many2many("ir.attachment", string="Documents")

    def upload_document(self):
        """Upload documents to the specified directory"""
        for attachment in self.attachment_ids:
            attachment.write(
                {
                    "res_model": "construction.document.directory",
                    "res_id": self.directory_id.id,
                }
            )

        return {"type": "ir.actions.act_window_close"}
