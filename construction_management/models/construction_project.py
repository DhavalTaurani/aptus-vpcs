# -*- coding: utf-8 -*-

from odoo import models, _, fields, api
from odoo.exceptions import ValidationError


class ConstructionProject(models.Model):
    _inherit = "project.project"

    is_construction = fields.Boolean(
        "Is Construction Project",
        default=False,
        help="Check this if the project is a construction project.",
    )

    # Construction-specific fields
    construction_type = fields.Selection(
        [
            ("residential", "Residential"),
            ("commercial", "Commercial"),
            ("infrastructure", "Infrastructure"),
            ("industrial", "Industrial"),
        ],
        string="Construction Type",
        tracking=True,
    )

    # Site information
    site_location = fields.Text("Site Location", tracking=True)
    site_coordinates = fields.Char("GPS Coordinates", tracking=True)
    site_address = fields.Text("Site Address")

    # Contract details
    contract_value = fields.Monetary(
        "Contract Value", currency_field="currency_id", tracking=True
    )
    contract_start_date = fields.Date("Contract Start Date", tracking=True)
    contract_end_date = fields.Date("Contract End Date", tracking=True)
    contract_duration = fields.Integer(
        "Contract Duration (Days)", compute="_compute_contract_duration", store=True
    )

    # Financial accounts for construction-specific transactions
    wip_account_id = fields.Many2one(
        "account.account",
        "Work in Progress Account",
        domain="[('account_type', '=', 'asset_current'), ('company_ids', 'in', [company_id])]",
        help="Account used for work in progress transactions",
    )
    retention_account_id = fields.Many2one(
        "account.account",
        "Retention Account",
        domain="[('account_type', '=', 'liability_current'), ('company_ids', 'in', [company_id])]",
        help="Account used for retention amounts",
    )



    # document_directory_ids = fields.One2many(
    #     "construction.document.directory",
    #     "project_id",
    #     string="Document Directories",
    #     help="Document directories for this project",
    # )

    construction_revenue_recognition_ids = fields.One2many(
        "construction.revenue.recognition",
        "project_id",
        string="Revenue Recognitions",
        help="Revenue recognition records for this project",
    )





    @api.depends("contract_start_date", "contract_end_date")
    def _compute_contract_duration(self):
        """Compute contract duration in days"""
        for project in self:
            if project.contract_start_date and project.contract_end_date:
                delta = project.contract_end_date - project.contract_start_date
                project.contract_duration = delta.days
            else:
                project.contract_duration = 0



    @api.constrains("contract_start_date", "contract_end_date")
    def _check_contract_dates(self):
        """Validate contract dates"""
        for project in self:
            if project.contract_start_date and project.contract_end_date:
                if project.contract_start_date > project.contract_end_date:
                    raise ValidationError(
                        "Contract start date cannot be after end date."
                    )

    @api.constrains("contract_value")
    def _check_contract_value(self):
        """Validate contract value"""
        for project in self:
            if project.contract_value and project.contract_value < 0:
                raise ValidationError("Contract value cannot be negative.")

    @api.constrains("site_coordinates")
    def _check_site_coordinates(self):
        """Validate GPS coordinates format"""
        for project in self:
            if project.site_coordinates:
                # Basic validation for GPS coordinates format (latitude, longitude)
                coords = project.site_coordinates.strip()
                if coords and "," in coords:
                    try:
                        lat, lng = coords.split(",")
                        lat_val = float(lat.strip())
                        lng_val = float(lng.strip())
                        if not (-90 <= lat_val <= 90) or not (-180 <= lng_val <= 180):
                            raise ValidationError(
                                "Invalid GPS coordinates. Latitude must be between -90 and 90, longitude between -180 and 180."
                            )
                    except ValueError:
                        raise ValidationError(
                            "GPS coordinates must be in format 'latitude, longitude' (e.g., '40.7128, -74.0060')"
                        )

    def action_view_boq_items(self):
        """Action to view BOQ items for this project"""
        action = self.env.ref("project.act_project_project_2_project_task_all").read()[
            0
        ]
        action["domain"] = [("project_id", "=", self.id), ("is_boq_item", "=", True)]
        action["context"] = {
            "default_project_id": self.id,
            "default_is_boq_item": True,
        }
        action["name"] = f"BOQ Items - {self.name}"
        return action



    @api.model_create_multi
    def create(self, vals_list):
        projects = super(ConstructionProject, self).create(vals_list)
        for project in projects:
            # project._create_default_document_directories()
            if project.is_construction:
                project._create_boq_stages()
        return projects

    # def _create_default_document_directories(self):
    #     default_directories = [
    #         {"name": "Drawings", "document_type": "drawings"},
    #         {"name": "Specifications", "document_type": "specifications"},
    #         {"name": "Submittals", "document_type": "submittals"},
    #         {"name": "Transmittals", "document_type": "transmittals"},
    #         {"name": "Reports", "document_type": "reports"},
    #         {"name": "Photos", "document_type": "photos"},
    #         {"name": "Contracts", "document_type": "contracts"},
    #         {"name": "Other", "document_type": "other"},
    #     ]
    #     for directory_vals in default_directories:
    #         self.env["construction.document.directory"].create(
    #             {
    #                 "name": directory_vals["name"],
    #                 "project_id": self.id,
    #                 "document_type": directory_vals["document_type"],
    #             }
    #         )
    
    def _create_boq_stages(self):
        """Create default BOQ stages for construction projects"""
        boq_stages = [
            {"name": "Draft", "sequence": 1, "fold": False},
            {"name": "In Review", "sequence": 2, "fold": False},
            {"name": "Approved", "sequence": 3, "fold": False},
            {"name": "Rejected", "sequence": 4, "fold": True},
            {"name": "Revision", "sequence": 5, "fold": False},
            {"name": "Done", "sequence": 6, "fold": True},
        ]
        
        for stage_vals in boq_stages:
            # Check if stage already exists
            existing_stage = self.env['project.task.type'].search([
                ('project_ids', 'in', [self.id]),
                ('name', '=', stage_vals['name'])
            ], limit=1)
            
            if not existing_stage:
                self.env['project.task.type'].create({
                    'name': stage_vals['name'],
                    'sequence': stage_vals['sequence'],
                    'fold': stage_vals['fold'],
                    'project_ids': [(4, self.id)],
                })




