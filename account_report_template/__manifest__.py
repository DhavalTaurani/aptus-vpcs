# -*- coding: utf-8 -*-
{
    'name': 'Account Report Template',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'author': 'VperfectCS',
    'summary': 'Create and manage account report templates',
    'depends': ['account'],
    'data': [
        'views/account_account_views.xml',
        'data/bs_report_data.xml',
        'data/pnl_report_data.xml',
        'views/account_report_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_report_template/static/src/components/oman_format_selection/oman_format_selection.js',
            'account_report_template/static/src/components/oman_format_selection/oman_format_selection.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
