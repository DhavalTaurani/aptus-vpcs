# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Order Global Discount (Same as Sales Discount)',
    'version': '19.0.1.0',
    'category': 'Purchase',
    'summary': 'Purchase Order Global Discount (Same as Sales Discount)',
    'description': """
    Purchase Order Global Discount (Same as Sales Discount)
""",
    'license': 'OPL-1',
    'author': 'BrowseInfo',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_order_discount_views.xml',
        'views/purchase_order_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
