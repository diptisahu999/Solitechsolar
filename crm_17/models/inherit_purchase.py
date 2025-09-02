from odoo import api, fields, models,_
from num2words import num2words
import re
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, float_round, format_date, groupby
import math
from odoo.tools import (
    formatLang
)
from datetime import date
from odoo.tools.misc import xlwt
import base64 
import io

class InheritPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    lot_line_ids = fields.One2many('lot.product.line','mst_id',string="Line")
    rpt_xls_file = fields.Binary()
    is_contener = fields.Boolean(string="Is Container")
    is_gen_lot = fields.Boolean(string="Is Generate Serail")

    def _prepare_picking(self):
        res = super(InheritPurchaseOrder, self)._prepare_picking()
        res.update({'is_contener': self.is_contener})
        return res 
    
    def generate_serail_number(self):
        line_list = []
        for rec in self:      
            self.lot_line_ids = False           
            last_seq_list = []
            for pu_line in self.order_line:
                line_list.append((0,0,{
                    'product_id':pu_line.product_id.id,
                    'qty':pu_line.product_qty,
                }))
            self.lot_line_ids = line_list
            
            for line in rec.lot_line_ids:
                product_id = line.product_id
                last_seq = product_id.last_seq or 0
                lot_rec = self.env['stock.lot'].sudo().search([('product_id', '=', product_id.id)],order="id desc",limit=1)
            
                if lot_rec and lot_rec.name:
                    match = re.search(r'\d+$', lot_rec.name[-5:])
                    if match:
                        if product_id.last_seq < int(match.group()):
                            last_seq = int(match.group())
                if not lot_rec:
                    last_seq = 0
                    
                for record in last_seq_list:
                    if record['product_id'] == line.product_id.id:
                        last_seq = record['last_seq']
                last_two_char = date.today().strftime('%Y')[-2:]
                batch_prefix = f"{product_id.barcode}Y{last_two_char}"
                lot_list = []
                for i in range(int(line.qty)):
                    if line.product_id:
                        last_seq += 1
                        batch_no = f"{batch_prefix}{str(last_seq).zfill(5)}"
                        lot_list.append((0,0,{'lot_name': batch_no}))
                line.line_ids = lot_list
                last_seq_list.append({'product_id': line.product_id.id,
                                        'last_seq': last_seq})
                product_id.last_seq = last_seq
        self.is_gen_lot = True
                

    def xlsx_report_lot(self):   
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Barcode')

        center_style = xlwt.easyxf(
            "align: vert centre, horiz centre; font: bold 1; border: top thin, right thin, bottom thin, left thin;"
        )

        worksheet.col(0).width = 8000 
        worksheet.col(1).width = 8000 
        worksheet.col(2).width = 8000 
        row = 0
        for rec in self.lot_line_ids:
            for line in rec.line_ids:

        # for index, line in enumerate(stock_lots, start=1):

                worksheet.write(row, 0, rec.product_id.barcode or "", center_style)

                worksheet.write(row, 1, line.lot_name or "", center_style)

                worksheet.write(row, 2, line.lot_name or "", center_style)

                row += 1

        fp = io.BytesIO()
        workbook.save(fp)
        self.rpt_xls_file = base64.encodebytes(fp.getvalue())

        return {
            'type': 'ir.actions.act_url',
            'name': 'stock.picking',
            'url': '/web/content/purchase.order/%s/rpt_xls_file/barcode_report_excel.xls?download=true' %(self.id),
        }
                    

class InheritPurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    image_128 = fields.Image(string="Image")
    remark_1 = fields.Text(string="Remark 1")
    remark_2 = fields.Text(string="Remark 2")
    remark_3 = fields.Text(string="Remark 3")
    attachment = fields.Binary(string="Attachment")

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        res = super(InheritPurchaseOrderLine,self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        if self.order_id.is_contener:
            res.update({'quantity': 0})
        return res
    
    @api.onchange('product_id')
    def onchange_sake_product_image(self):
    	for product in self:
    		product.image_128 = product.product_id.image_128
              
class LotProductLine(models.Model):
    _name = "lot.product.line"
    _description = "Lot Details Line"

    mst_id = fields.Many2one('purchase.order',string="Mst")

    product_id = fields.Many2one('product.product',string="Product")
    qty = fields.Integer(string="Qty")
    line_ids = fields.One2many('lot.details','mst_id',string="Line")

class LotDetails(models.Model):
    _name = "lot.details"
    _description = "Lot Details"

    mst_id = fields.Many2one('lot.product.line',string="Mst")

    lot_name = fields.Char(string="Lot/Serial Number")

class InheritPurchaseReport(models.Model):
    _inherit = "purchase.report"

    remaining_qty = fields.Float('Qty Remaining', readonly=True)

    def _select(self):
        res = super(InheritPurchaseReport,self)._select()
        res = res + """ ,
                    sum(l.product_qty / line_uom.factor * product_uom.factor)- 
                    sum(l.qty_received / line_uom.factor * product_uom.factor) as remaining_qty """
        return res