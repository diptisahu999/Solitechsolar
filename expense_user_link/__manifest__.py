{
    'name': 'Expense User Link',
    'version': '17.0.1.0.0',
    'summary': 'Show all users in Expense Employee field',
    'category': 'Human Resources',
    'author': 'Pratham',
    'depends': ['hr_expense'],
    'data': [
    'views/hr_expense_view_inherit.xml', 
    'data/user_employee_data.xml',
],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}