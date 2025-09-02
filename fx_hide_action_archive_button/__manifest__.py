{
    "name": "Hide Action Archive Button",
    "summary": "Hide Action Archive Button",
    "version": "17.0",
    "description": """Hide Action Archive Button""",
    "author": "Doan Thanh Sang",
    "category": "Extra Tools",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "views/inherit_res_users_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "fx_hide_action_archive_button/static/src/**/*",
        ]
    },
    "installable": True,
    "auto_install": False,
    "application": True,
    "images": [
        'static/description/icon.png',
    ],
}
