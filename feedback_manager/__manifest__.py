{
    "name": "Feedback Manager",
    "summary": "Feedback capture with reports and permissions",
    "version": "17.0.2.0.0",
    "category": "Operations/Feedback",
    "author": "Pratham",
    "license": "LGPL-3",
    "website": "https://example.com",
    "depends": ["base", "web", "mail","sales_team"],

    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "views/feedback_views.xml",         
    ],

    "application": True,
    "installable": True,
}
