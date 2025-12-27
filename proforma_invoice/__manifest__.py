{
    'name': 'Proforma Invoicing',
    'version': '17.0.2.0',
    'summary': 'Proforma Invoicing',
    'author': 'Diptiranjan',
    'category': 'Sales',
    'depends': ['base', 'mail','sale', 'product', 'sale_management', 'project', 'contacts', 'crm', 'web','l10n_in', 'account'],
    'data': [
        'report/proforma_invoice.xml',
        'data/sales_dashboard_data.xml',
        'data/proforma_invoice_data.xml',
        'data/ir_sequence_data.xml',
        'views/sales_dashboard_views.xml',
        'views/proforma_invoice_views.xml',
        'views/crm_lead_views.xml',
        'views/custom_sale_order_views.xml', 
        'views/sale_order_views.xml',
        'views/proforma_wizard_views.xml',
        'views/quotation_action_fix.xml',
        'security/ir.model.access.csv',
        'security/proforma_invoice_security.xml',
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