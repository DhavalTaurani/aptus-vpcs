# -*- coding: utf-8 -*-
{
    "name": "Construction Management",
    "version": "19.0.1.0.0",
    "category": "Project",
    "summary": "Comprehensive construction project management system",
    "description": """
Construction Management System
==============================

A comprehensive construction project management system built on Odoo 19 Enterprise
that provides:

* Project hierarchy management with phases and work packages
* Bill of Quantities (BOQ) management and tracking
* Cost code management integrated with product catalog
* Procurement integration with purchase and inventory
* Subcontractor management and progress tracking
* Document management and submittal workflows
* Financial integration with accounting and analytics
* Quality and safety management tools
* Mobile-friendly interface for field operations

This module extends Odoo's standard project management capabilities with
construction-specific functionality while maintaining full integration
with existing Odoo modules.
    """,
    "author": "VPerfectCS",
    "website": "https://www.vperfectcs.com",
    "license": "LGPL-3",
    "depends": [
        # Core Odoo modules
        "base",
        "mail",
        "portal",
        "web",
        "board",  # Added board module dependency
        # Project management
        "project",
        "project_account",
        "sale_project",
        # Procurement and inventory
        "purchase",
        "stock",
        "stock_account",
        # Accounting and analytics
        "account",
        "analytic",
        # Supporting modules
        "rating",
        "resource",
        "hr_timesheet",
        "digest",
    ],
    "data": [
        # Security
        "security/construction_security.xml",
        "security/construction_template_security.xml",
        "security/ir.model.access.csv",
        # Data - Load data files first
        "data/construction_data.xml",
        "data/construction_sequence.xml",
        "data/construction_cost_codes.xml",
        "data/construction_templates.xml",
        "data/construction_email_templates.xml",
        "data/construction_cron.xml",
        # Menus - Load menus early as other views might depend on them
        "views/construction_menu.xml",
        # Views - Core Models
        "views/construction_project_views.xml",
        "views/construction_task_views.xml",
        "views/construction_cost_code_views.xml",
        "views/construction_template_views.xml",
        "views/construction_template_analytics_views.xml",
        "views/construction_template_import_export_views.xml",
        "views/product_template_views.xml",
        # Views - Procurement & Purchase
        # Views - Subcontractor Management
        "views/construction_subcontractor_views.xml",
        "views/construction_subcontractor_kanban_view.xml",
        "views/construction_subcontractor_performance_views.xml",
        # Views - Document Management
        "views/construction_document_directory_views.xml",
        "views/construction_submittal_views.xml",
        "views/construction_document_reports_views.xml",
        # Views - Financial Management
        "views/construction_revenue_recognition_views.xml",
        # Views - Quality & Safety Management
        "views/construction_quality_views.xml",
        "views/construction_incident_views.xml",
        # Wizards
        "wizard/assign_subcontractor.xml",
        "wizard/generate_purchase_order.xml",
        "wizard/construction_progress_update_views.xml",
        "wizard/construction_cost_allocation_views.xml",
        # 'wizard/construction_boq_import_views.xml',
        "wizard/construction_upload_document_views.xml",
        "wizard/construction_template_customization_views.xml",
        "views/wizard_menus.xml",
        # Reports
        "report/revenue_recognition_report.xml",
        # 'report/construction_boq_report.xml',
        # 'report/construction_cost_report.xml',
    ],
    "demo": [
        # Demo data temporarily disabled to ensure clean installation
        # Users can manually create demo data using the template system
        # "demo/construction_partners.xml",
        # "demo/construction_products.xml",
        # "demo/construction_cost_codes.xml",
        # "demo/construction_projects.xml",
        # "demo/construction_subcontractors.xml",
        # "demo/construction_documents.xml",
        # "demo/construction_demo.xml",
        # "demo/construction_template_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "construction_management/static/src/css/construction.css",
            "construction_management/static/src/js/construction_dashboard.js",
            "construction_management/static/src/js/construction_kanban.js",
        ],
        "web.assets_frontend": [
            "construction_management/static/src/css/construction_portal.css",
        ],
    },
    "images": [
        "static/description/banner.png",
        "static/description/icon.png",
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "sequence": 10,
    "external_dependencies": {
        "python": [],
    },
    "test": [
        "tests/test_construction_project.py",
        "tests/test_template_management.py",
    ],
    "price": 299,
    "currency": "EUR",
}
