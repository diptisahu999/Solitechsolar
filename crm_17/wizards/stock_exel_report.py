from odoo import api, models, fields
from datetime import date,datetime
from bs4 import BeautifulSoup 
import datetime
from odoo.tools.misc import xlwt
import base64 
import io
from odoo.exceptions import ValidationError

class StockExelWiz(models.TransientModel):
    _name = 'stock.exel.wiz'
    _description= "Stock Report Exel"

    rpt_xls_file = fields.Binary()
    product_ids = fields.Many2many('product.product', string='Products')
    select = fields.Selection([
        ('All', 'All'),
        ('Select', 'Select')], string="Select",default='All')
    
    def stock_xls_report(self): 
        self.rpt_xls_file = False  
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Stock')

        header_style = xlwt.easyxf(
            "pattern: pattern solid, fore_colour green; font: bold 1, colour white; "
            "align: vert centre, horiz centre; "
            "border: top thick, right thick, bottom thick, left thick;"
        )
        center_style = xlwt.easyxf(
            "align: vert centre, horiz centre; font: bold 1; border: top thin, right thin, bottom thin, left thin;"
        )

        headers = ["SR. NO.", "CODE", "ERP LOCATION", "QTY", "Rate", "Amount", "INWARD DATE", "COMPANY NAME", "INVOICE NO."]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_style)

        worksheet.col(0).width = 2000
        worksheet.col(1).width = 8000
        worksheet.col(2).width = 8000
        worksheet.col(3).width = 6000
        worksheet.col(4).width = 6000
        worksheet.col(5).width = 6000
        worksheet.col(6).width = 8000
        worksheet.col(7).width = 8000
        worksheet.col(8).width = 8000

        row = 1
        srl = 1
        domain = [('product_qty', '>', 0)]
        if self.select == 'Select' and self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids)) 

        stock_lots = self.env['stock.lot'].sudo().search(domain)
        if not stock_lots:
            raise ValidationError("No Stock.")

        grouped_lots = {}
        for lot in stock_lots:
            key = (lot.product_id.id, lot.inward_date, lot.location_id.id)
            if key not in grouped_lots:
                grouped_lots[key] = []
            grouped_lots[key].append(lot)

        for (product_id, inward_date, location_id), lots in grouped_lots.items():
            product = self.env['product.product'].sudo().browse(product_id)
            location = self.env['stock.location'].sudo().browse(location_id)
            total_qty = sum(lot.product_qty for lot in lots)
            rate = 0.0
            note_text = ""
            ref = ""

            for lot in lots:
                if rate == 0.0 and lot.rate: 
                    rate = lot.rate

                if not note_text and lot.note: 
                    soup = BeautifulSoup(lot.note, 'html.parser')
                    note_text = soup.get_text(strip=True)

                if not ref and lot.ref:
                    ref = lot.ref or ""

            amount = total_qty * rate
            if inward_date and isinstance(inward_date, (datetime.datetime, datetime.date)):  
                inward_date_str = inward_date.strftime('%d-%m-%Y')  
            else:  
                inward_date_str = ""
                
            worksheet.write(row, 0, srl, center_style)  
            worksheet.write(row, 1, product.barcode or "", center_style)
            worksheet.write(row, 2, location.complete_name or "", center_style)
            worksheet.write(row, 3, total_qty or 0, center_style)
            worksheet.write(row, 4, f"{rate:.2f}" if rate else 0, center_style)
            worksheet.write(row, 5, f"{amount:.2f}" if rate else 0, center_style)
            worksheet.write(row, 6, inward_date_str or "", center_style)
            worksheet.write(row, 7, note_text, center_style)
            worksheet.write(row, 8, ref, center_style)

            row += 1
            srl += 1

        fp = io.BytesIO()
        workbook.save(fp)
        self.rpt_xls_file = base64.encodebytes(fp.getvalue())

        return {
            'type': 'ir.actions.act_url',
            'name': 'stock.exel.wiz',
            'url': '/web/content/stock.exel.wiz/%s/rpt_xls_file/stock_report_excel.xls?download=true' %(self.id),
        }
    

class PurchaseStockExelWiz(models.TransientModel):
    _name = 'purchase.stock.exel.wiz'
    _description= "Purchase Stock Report Exel"

    rpt_xls_file = fields.Binary()
    purchase_ids = fields.Many2many('purchase.order', string='PO')
    
    def purchase_stock_xls_report(self): 
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Purchase Stock')

        header_style = xlwt.easyxf(
            "pattern: pattern solid, fore_colour green; font: bold 1, colour white; "
            "align: vert centre, horiz centre; "
            "border: top thick, right thick, bottom thick, left thick;"
        )
        center_style = xlwt.easyxf(
            "align: vert centre, horiz centre; font: bold 1; border: top thin, right thin, bottom thin, left thin;"
        )

        headers = ["PO NO.", "CODE", "PRODUCT NAME", "ORDER QTY", "RECEIVED QTY"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_style)

        worksheet.col(0).width = 5000
        worksheet.col(1).width = 6000
        worksheet.col(2).width = 10000
        worksheet.col(3).width = 6000
        worksheet.col(4).width = 6000
      
        row = 1
        srl = 1
        domain = [('picking_code', '=', 'incoming'),('state', '=', 'done')]
        if self.purchase_ids:
            domain.append(('purchase_id', 'in', self.purchase_ids.ids)) 

        stock_lots = self.env['stock.move'].sudo().search(domain)
        if not stock_lots.filtered(lambda x: x.purchase_id):
            raise ValidationError("No Stock.")

        for lot in stock_lots.filtered(lambda x: x.purchase_id):
            worksheet.write(row, 0, lot.purchase_id.name or "", center_style)  
            worksheet.write(row, 1, lot.product_id.barcode or "", center_style)
            worksheet.write(row, 2, lot.product_id.name or "", center_style)
            worksheet.write(row, 3, sum(lot.purchase_id.order_line.filtered(lambda x: x.product_id == lot.product_id).mapped('product_qty')) or 0, center_style)
            worksheet.write(row, 4, lot.quantity or 0, center_style)

            row += 1
            srl += 1

        fp = io.BytesIO()
        workbook.save(fp)
        self.rpt_xls_file = base64.encodebytes(fp.getvalue())

        return {
            'type': 'ir.actions.act_url',
            'name': 'stock.exel.wiz',
            'url': '/web/content/purchase.stock.exel.wiz/%s/rpt_xls_file/Purchase Stock Report excel.xls?download=true' %(self.id),
        }