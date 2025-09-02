{
    "name": "Web Notify",
    "summary": """
        Send notification messages to user""",
    "version": "17.0",
    "license": "AGPL-3",
    "author": "Dolphy",
    "development_status": "Production/Stable",
    "depends": ["web", "bus", "base", "mail"],
    "assets": {
        "web.assets_backend": [
            "web_notify/static/src/js/services/*.js",
        ]
    },
    "demo": ["views/res_users_demo.xml"],
    "installable": True,
}
