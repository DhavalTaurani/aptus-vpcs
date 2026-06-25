{
    'name': 'Aptus-Macrofix Customizations',
    'version': '19.0.1.0',
    'summary': """
        All Customizations are under this module
    """,
    'category': 'General Reports',
    'author': 'Macrofix',
    'description':
        """
        Customer Requirements are converted into Custom Modules
        """,
    'data': [
        'security/ir.model.access.csv',
        'reports/sale_quotation_report.xml',
        'data/mail_template_data.xml',
        # 'reports/sale_quotation_report_elv.xml',
        'reports/sale_invoice_report.xml',
        'reports/purchase_report_elv.xml',
        'reports/purchase_report_soft.xml',
        'reports/purchase_invoice_soft.xml',
        'reports/purchase_invoice_elv.xml',
        'reports/delivery_order_report.xml',
        'reports/journal_voucher.xml',
        'reports/receipt_and_payment_voucher.xml',
        'views/sale_order_view.xml',
        'views/res_company_view.xml',
        'views/purchase_views.xml',
        'views/hr_employee.xml',
        'views/account.xml',
        'views/purchase.xml',
        'views/product.xml',
        'views/move_line.xml',
    ],
    'depends': ['purchase','stock','sale', 'delivery', 'sale_timesheet','hr', 'hr_org_chart'],

    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
# -*- coding: utf-8 -*-
