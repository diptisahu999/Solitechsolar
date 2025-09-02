# -*- coding: utf-8 -*-
{
    'name' : 'Account Type',
    'version' : '17.11',
    'summary': "General Ledger Trial Balance Ageing Balance Sheet Profit and Loss Cash Flow Dynamic Analytic Reproting",
    'sequence': 15,
    'description': """
                    Odoo 17 Full Accountin
                    """,
    'category': 'Accounting/Accounting',
    'website': '',
    'depends': ['account', 'web'],
    'data': [
             'security/ir.model.access.csv',
             'views/account_type.xml',
             ],
    'demo': [],
    'assets': {
        'web.assets_backend': [
        'account_type/static/src/components/**/*',
        ],
    },
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}
