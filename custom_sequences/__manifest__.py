{
    'name': 'Sequence Customizations',
    'author': 'Macrofix',
    'website': 'https://www.macrofix.com',
    'version': '19.0.2.0',
    'depends': ['account', 'sale', 'purchase', 'project', 'stock'],
    'data': [
        'data/account_move.xml',
        'data/account_payment.xml',
        'data/journal_sequence.xml',
        'data/sale_sequence.xml',
        'data/purchase_sequence.xml',
        'data/stock_move_sequence.xml',
        'data/project_sequence.xml',
        'data/account_payment_pdc.xml',
        'views/project_views.xml',
        'views/account_journal.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3'
}