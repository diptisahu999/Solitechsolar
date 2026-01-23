{
    'name': 'app module access',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Customizations for app access',
    'description': """
        This module contains customizations for Sales.
        - Removes 'New' button from Quotation List and Kanban views.
    """,
    'depends': ['sale'],
    'data': [
        'security/rv_sale_security.xml',
        'views/ir_ui_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}