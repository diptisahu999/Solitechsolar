import re

manifest_path = r'proforma_invoice\__manifest__.py'

with open(manifest_path, 'r') as f:
    content = f.read()

# Add the new security file after the first access.csv
if "'security/ir.model.access_wizard.csv'," not in content:
    content = content.replace(
        "'security/ir.model.access.csv',",
        "'security/ir.model.access.csv',\n        'security/ir.model.access_wizard.csv',"
    )
    
    with open(manifest_path, 'w') as f:
        f.write(content)
    print('Manifest updated successfully')
else:
    print('Wizard access already present in manifest')
