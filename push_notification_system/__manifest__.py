{
    'name': "Push Notification System",
    'version': '17.0.1.0.0',
    'summary': "Sends real-time UI notifications for business events.",
    'author': "Your Name",
    'category': 'Tools',
    'depends': ['base', 'web', 'bus'],
    'assets': {
        'web.assets_backend': [
            'push_notification_system/static/src/js/push_notification.js',
        ],
    },
    'application': False,
    'installable': True,
}