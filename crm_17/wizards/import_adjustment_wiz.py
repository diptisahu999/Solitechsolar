import openpyxl
import tempfile
import binascii
import xlrd
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

class ImportAdjustmentWizard(models.TransientModel):
    _name = 'import.adjustment.wiz'
    _description = 'Import Inventory Adjustments Data into Odoo Model'

    # Define fields in your model here
    import_file = fields.Binary(string="File to Import")

    def action_import_file(self):
        try:
            if not self.import_file:
                raise UserError(_("Please upload a file to import."))

            # Create a temporary file for the uploaded file
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.import_file))
            fp.seek(0)
            fp.close()

            # Load workbook and get the active sheet
            workbook = openpyxl.load_workbook(fp.name, data_only=True)
            sheet = workbook.active  # Default to the first sheet

            # Extract headers from the first row
            headers = [cell.value for cell in sheet[1]]  # First row as headers

            # Prepare data for bulk creation
            lots_data = []  # List for stock.lot creation
            quants_data = []  # List for stock.quant creation
            skipped_products = [] 
            for row in sheet.iter_rows(min_row=2, values_only=True):  # Start processing from row 2
                data = dict(zip(headers, row))

                # Process product code
                product_code = data.get('CODE', False)
                if product_code:
                    # Search for product
                    product_code = str(product_code).strip() if product_code else None
                    product_rec = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
                    if not product_rec:
                        raise UserError(f"Product with code {product_code} not found in the system.")
                    if product_rec.detailed_type != 'product':
                        # Append skipped product name and skip processing this row
                        skipped_products.append(product_rec.display_name)
                        continue
                    # Process location
                    location_name = str(data.get('ERP LOCATION', '')).strip()
                    location_rec = self.env['stock.location'].search([('complete_name', '=', location_name)], limit=1)
                    if not location_rec:
                        raise UserError(f"Location with name {location_name} not found in the system.")

                    # Process inward date
                    inward_date_raw = data.get('INWARD DATE')
                    if inward_date_raw:
                        if isinstance(inward_date_raw, datetime):
                            inward_date = inward_date_raw.strftime('%Y-%m-%d')
                        else:
                            try:
                                inward_date = datetime.strptime(str(inward_date_raw).strip(), '%d/%m/%Y')
                            except ValueError:
                                raise UserError(f"Invalid date format for INWARD DATE: {inward_date_raw}. Expected format is 'DD/MM/YYYY'.")
                    else:
                        inward_date = None

                    # Generate batch serial number
                    if isinstance(data.get('INWARD DATE'), str):
                        last_two_char = data.get('INWARD DATE')[-2:]
                    elif isinstance(data.get('INWARD DATE'), datetime):
                        last_two_char = data.get('INWARD DATE').strftime('%Y')[-2:]
                    batch_prefix = f"{product_rec.barcode}Y{last_two_char}"
                    last_seq = product_rec.last_seq or 0

                    # Process quantity
                    qty = int(data.get('QTY', 0))
                    for i in range(qty):
                        last_seq += 1
                        batch_no = f"{batch_prefix}{str(last_seq).zfill(5)}"

                        # Prepare values for stock.lot
                        lot_vals = {
                            'name': batch_no,
                            'product_id': product_rec.id,
                            'location_id': location_rec.id,
                            'company_id': self.env.company.id,
                            'inward_date': inward_date,
                            'ref': data.get('INVOICE NO.', ''),
                            'note': data.get('COMPANY NAME', ''),
                            'rate': data.get('Rate', 0),
                        }
                        lots_data.append(lot_vals)
                        # Prepare values for stock.quant
                        quant_vals = {
                            'lot_id': None,  # This will be linked after lot creation
                            'product_id': product_rec.id,
                            'location_id': location_rec.id,
                            'quantity': 1,
                            'company_id': self.env.company.id,
                        }
                        quants_data.append((batch_no, quant_vals))  # Store batch_no for later linking

                    # Update last_seq for the product
                    product_rec.last_seq = last_seq
            print("========skipped_products=========",skipped_products)
            # Bulk create stock.lot records
            lot_records = self.env['stock.lot'].create(lots_data)

            # Map lot names to their IDs for linking in stock.quant
            lot_name_to_id = {lot.name: lot.id for lot in lot_records}

            # Link lot IDs and prepare for bulk creation of stock.quant
            for batch_no, quant_vals in quants_data:
                quant_vals['lot_id'] = lot_name_to_id.get(batch_no)

            # Bulk create stock.quant records
            self.env['stock.quant'].create([vals for _, vals in quants_data])

            workbook.close()
            return True

        except Exception as e:
            raise UserError(_("Error importing file: %s") % e)
