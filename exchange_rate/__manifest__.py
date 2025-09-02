# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Currency Wise Pricelist',
    'sequence': 1,
    'version': '17.0',
    'summary': 'crm odoo 17',
    'depends': ['base','crm_17'],

    'data': [
            # 'security/ir.model.access.csv',
            'views/inherit_sale_order.xml',
            ],

    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
