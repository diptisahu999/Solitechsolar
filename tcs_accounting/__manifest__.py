{
    'name': 'TCS and TDS in Indian Taxation System',
    'version': '17.0',
    'summary': 'TDS (Tax Deducted at Source) and TCS (Tax Collected at Source) are key components of the Indian taxation system. TDS involves deducting tax at the source of income, applicable to various earnings like salaries, interest, and payments to contractors. On the other hand, TCS requires sellers to collect a percentage of the sales value as tax from buyers at the time of sale. Both mechanisms are designed to ensure efficient tax collection and prevent tax evasion in India.'
               '',
    'sequence': 1,
    'price': 57.50,
    'description': """ TCS and TDS Management: Simplifying Tax Calculations for Indian Companies '
               ' """,
    'author': "AppsComp Widgets Pvt Ltd",
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'website': "www.appscomp.com",
    'category': 'Accounting',
    'depends': [
        'base', 'account', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/tcs_accounting.xml',
        'views/res_partner_inherited.xml',
        'views/res_config_view.xml',
        'views/tds_accounting.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ],
        'web.assets_tests': [
        ],
    },
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
