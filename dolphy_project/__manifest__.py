# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Dolphy Project',
    'sequence': 1,
    'version': '17.0',
    'summary': 'dolphy project',
    'depends': ['base','project','sale_project'],

    'data': [
            'security/ir.model.access.csv',
            'security/rule_security.xml',
            
            'wizards/project_details_wiz.xml',
            
            'views/inherit_project.xml',
            'views/project_master.xml',
            'views/master_menu.xml',
            ],

    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
