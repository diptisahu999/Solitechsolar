{
    'name': 'Proforma Invoicing with Sales Dashboard',
    'version': '17.0.2.0',
    'summary': 'Comprehensive Sales Dashboard with Proforma Invoicing',
    'author': 'Pratham',
    'category': 'Sales',
    'depends': ['base', 'mail', 'product', 'sale_management', 'project', 'crm', 'web'],
    'data': [
        'report/proforma_invoice.xml',
        'data/sales_dashboard_data.xml',
        'views/sales_dashboard_views.xml',
        'views/proforma_invoice_views.xml',
        'views/sale_order_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            ('include', 'web._assets_helpers'),
            'proforma_invoice/static/lib/chartjs/chart.umd.min.js',
            
            # Dashboard files
            'proforma_invoice/static/src/components/dashboard/sales_dashboard.scss',
            'proforma_invoice/static/src/components/dashboard/sales_dashboard.js',
            'proforma_invoice/static/src/components/dashboard/sales_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}