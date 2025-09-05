{
    'name': 'Proforma Invoicing (Non-Accounting)',
    'version': '17.0.1.0',
    'summary': 'Create and manage Proforma Invoices completely separate from the accounting module.',
    'author': 'Your Name',
    'category': 'Sales',
    'depends': ['base', 'mail', 'product', 'sale_management', 'project'],
    'data': [
    'views/proforma_invoice_views.xml',
    'views/sale_order_views.xml',
    'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}