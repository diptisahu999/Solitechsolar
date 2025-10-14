# -*- coding: utf-8 -*-
{
    'name': "Flutter WebView Bridge",
    'version': '17.0.1.0.0',
    'summary': """
        Intercepts web notifications and sends them to a Flutter WebView app
        via a JavaScript bridge.""",
    'description': """
        This module patches the core notification service to forward messages
        to a JavaScript channel named 'OdooNotificationBridge'.
    """,
    'author': "Pratham Rangunwala",
    'category': 'Extra Tools',
    'depends': [
        'web',  
        'mail', 
    ],
    'assets': {
        'web.assets_backend': [
            'my_flutter_bridge/static/src/js/notification_bridge.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}