{
    'name': 'CRM Business Card Scanner',
    'version': '17.0.1.0.0',
    'summary': 'Scan business cards to create leads using OCR.',
    'author': 'Your Name',
    'website': 'Your Website',
    'category': 'Sales/CRM',
    'depends': ['crm'],
    'data': [
        'views/crm_lead_views.xml',
        'views/business_card_scanner_wizard_views.xml',
        # 'wizards/business_card_scanner_wizard_views.xml',
        'security/ir.model.access.csv',
    ],
    'external_dependencies': {
        'python': ['pytesseract'],
    },
    'installable': True,
    'application': False,
}