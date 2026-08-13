# -*- coding: utf-8 -*-
{
    'name': 'Solitech Login Customization',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Hides unnecessary links on the login page',
    'description': """
        This module hides the following elements from the Odoo login page:
        - Don't have an account?
        - Reset Password
        - Manage Databases
        - Powered by Odoo
    """,
    'depends': ['web', 'auth_signup'],
    'data': [
        'views/login_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
