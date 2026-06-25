{
    'name': "Purchase/Sales Toolkit",

    'summary': "Module to enhance Purchase and Sales Orders",

    'description': """This module provides tools to enhance Purchase and Sales Orders with additional functionality and synchronization features.""",
    'version': '0.1',

    "author": "VPerfectCS",
    "website": "https://www.vperfectcs.com",
    'license': 'LGPL-3',
    'category': 'Extra Tools',
    'depends': ['purchase', 'sale', 'aptus_macrofix_customizations'],
    'data': [
        'views/purchase_order.xml',
        'views/hr_leave.xml',
    ],
    'installable': True,
    'application': True,
}

