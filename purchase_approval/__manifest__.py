# -*- coding: utf-8 -*-
{
    'name': 'PO Dynamic Approval',
    'version': '19.0.1.0',
    'summary': """
    Dynamic approval for purchase orders
    
    """,
    'category': 'Purchases',
    'author': 'AK',
    'description':
        """
Purchase Order Approval 
        """,
    'data': [
        'security/ir.model.access.csv',
        'data/purchase_approval_route.xml',
        'views/purchase_approval_route.xml',
        'views/res_config_settings_views.xml',
    ],
    'depends': ['purchase'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
