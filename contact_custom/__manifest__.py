# -*- coding: utf-8 -*-

{
    'name': 'Contact Custom',
    'version': '19.0.1.0',
    'category': 'Sales/CRM',
    'summary': 'Extending the contact base functionality to add customizations',
    'description': """
        This module provides additional functionalities to the contact addons fields details.
    """,
    'website': '',
    'author': "Macofix",

    'depends': [
        'base',
        'contacts'
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml'
    ],

    'installable': True,
    'license': 'LGPL-3',
}
