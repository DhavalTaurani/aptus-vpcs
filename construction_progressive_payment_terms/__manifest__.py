# -*- coding: utf-8 -*-
{
    "name": "Construction Progressive Payment Terms",
    "version": "19.0.1.0.1",
    "category": "Accounting/Accounting",
    "summary": "Progressive payment terms for construction projects with milestone-based payments",
    "description": """
Construction Progressive Payment Terms
======================================

This module extends Odoo's standard payment terms functionality to support 
dynamic, milestone-based payment scheduling for construction projects.

Key Features:
* Progressive payment term templates for different construction categories
* Milestone-based payment scheduling (Advance, Material Delivery, Installation, Testing & Commissioning, Retention)
* Dynamic payment term configuration at sale order level
* Integration with existing construction management modules
* Support for sub-milestones and partial deliveries
* Comprehensive milestone tracking and approval workflows

The module is designed to work with any construction category (ELV, MEP, Civil, 
Structural, etc.) while providing flexible templates for quick setup and full 
customization capabilities.
    """,
    "author": "VPerfectCS",
    "website": "https://www.vperfectcs.com",
    "license": "LGPL-3",
    "depends": [
        # Core Odoo modules
        "base",
        "mail",
        "web",
        # Accounting modules
        "account",
        "analytic",
        # Sales modules
        "sale",
        "sale_project",
        # Project management
        "project",
        # Construction modules
        "construction_management",
    ],
    "data": [
        # Security
        "security/progressive_payment_security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/progressive_payment_template_data.xml",
        "data/sub_milestone_templates.xml",
        "data/elv_aptus_ppt_progressive_payment.xml",
        # Views
        "views/account_payment_term_views.xml",
        "views/account_payment_term_line_views.xml",
        "views/account_payment_term_sub_template_views.xml",
        "views/sale_order_payment_milestone_views.xml",
        "views/milestone_invoice_wizard_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/construction_integration_views.xml",
        "views/progressive_payment_menu.xml",
    ],
    "demo": [
        "demo/progressive_payment_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "construction_progressive_payment_terms/static/src/css/progressive_payment.css",
            "construction_progressive_payment_terms/static/src/js/progressive_payment_widget.js",
        ],
    },
    "images": [
        "static/description/icon.png",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "sequence": 15,
    "external_dependencies": {
        "python": [],
    },
    "price": 399,
    "currency": "EUR",
}