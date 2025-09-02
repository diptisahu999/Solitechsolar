{
    'name': "Demo Task Application",
    'version': '17.0.1.0.0',
    'summary': "A simple app to generate events for push notification testing.",
    'author': "Your Name",
    'category': 'Productivity',
    'depends': ['base', 'mail'],
    'data': [
        'security/demo_task_security.xml',
        'security/ir.model.access.csv',
        'data/scheduled_actions.xml', # Added scheduled action
        'views/demo_task_views.xml',
        'views/demo_task_menus.xml',
    ],
    'application': True,
    'installable': True,
}