# -*- coding: utf-8 -*-
{
    'name': 'ZKTeco Attendance Integration',
    'version': '1.0',
    'category': 'Human Resources/Attendance',
    'summary': 'Integrate ZKTeco BioTime biometric attendance with Odoo hr.attendance',
    'description': """
ZKTeco Attendance Integration
=============================
Connects Odoo to the ZKTeco BioTime 9.5 API.
Features:
- Dynamic authentication token generation
- Map employees via punch_id
- Scheduled cron job for syncing attendance
    """,
    'author': 'VperfectCS',
    'depends': ['hr_attendance'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/server_actions.xml',
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
