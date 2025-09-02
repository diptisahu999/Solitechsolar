from odoo import api, fields, models,_
from num2words import num2words
import re
from odoo.exceptions import UserError
from odoo.tools.misc import xlwt
import base64 
import io
import os
from PIL import Image
from io import BytesIO
import xlsxwriter
from odoo.tools import base64_to_image
from odoo import tools
import tempfile
class TechvProductPricelist(models.Model):
    _name = "techv.product.pricelist"
    _description= "Pricelist for combo product"

    name = fields.Char(string='Name')
    line_ids = fields.One2many('techv.product.pricelist.line','mst_id',string="Pricelist")
    rpt_xls_file = fields.Binary()

    def action_xlxs_report(self):

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Pricelist')

        center_style = xlwt.easyxf(
            "align: vert centre, horiz centre; font: bold 1; border: top thin, right thin, bottom thin, left thin;"
        )
        green_header_style = xlwt.easyxf(
            "pattern: pattern solid, fore_colour green; font: bold 1, colour white; "
            "align: vert centre, horiz centre; "
            "border: top thick, right thick, bottom thick, left thick;"
        )

        image_cell_style = xlwt.easyxf(
            "border: top thin, right thin, bottom thin, left thin;" 
        )

        data_format = xlwt.easyxf(
            "font: bold 0; border: top thin, right thin, bottom thin, left thin; align: vert centre, horiz left;"
        )

        headers = ["Sr. No.", "Product Image", "Product Code", "Product Name", "Product Specification", "Product Rates"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, green_header_style)

        worksheet.col(0).width = 2000 
        worksheet.col(1).width = 3500 
        worksheet.col(2).width = 8000  
        worksheet.col(3).width = 10000  
        worksheet.col(4).width = 12000  
        worksheet.col(5).width = 6000  

        # Data rows
        row = 1
        for index, line in enumerate(self.line_ids, start=1):
            worksheet.write(row, 0, index, center_style)
            worksheet.row(row).height = 3200
            if line.image_128:
                # pil_image = base64_to_image(line.image_128)
                # pil_image = pil_image.resize((50, 50))
                # im = pil_image
                # image_parts = im.split()
                # r = image_parts[0]
                # g = image_parts[1]
                # b = image_parts[2]
                # img = Image.merge("RGB", (r, g, b))
                # fo = io.BytesIO()
                # img.save(fo, format='bmp')

                # logo_data = base64_to_image(line.image_128)
                # # logo_image = Image.open(io.BytesIO(logo_data))

                # # Resize the image to fit into the cell
                # logo_image = logo_data.resize((50, 50))  # Resize to 100x100 pixels
                # fo = io.BytesIO()
                # logo_image.save(fo, format='bmp')
                # fo.seek(0)

                # worksheet.insert_bitmap_data(fo.getvalue(), row, 1)
                logo_data = base64_to_image(line.image_128)
                
                logo_image = logo_data.resize((61, 17))  # hieght and widht

                fo = io.BytesIO()
                logo_image = logo_image.convert("RGB") 
                logo_image.save(fo, format='bmp')
                fo.seek(0)

                worksheet.write(row, 1, "", image_cell_style)
                worksheet.insert_bitmap_data(fo.getvalue(), row, 1,)

            worksheet.write(row, 2, line.product_id.barcode or "", data_format)

            worksheet.write(row, 3, line.product_id.name or "", data_format)

            worksheet.write(row, 4, line.product_id.description_sale if line.product_id.description_sale else line.product_id.name , data_format)

            worksheet.write(row, 5, line.product_id.list_price or 0.0, center_style)
            row += 1

        fp = io.BytesIO()
        workbook.save(fp)
        self.rpt_xls_file = base64.encodebytes(fp.getvalue())

        return {
            'type': 'ir.actions.act_url',
            'name': 'techv.product.pricelist',
            'url': '/web/content/techv.product.pricelist/%s/rpt_xls_file/pricelist_report_excel.xls?download=true' %(self.id),
        }

class ProductPricelistLine(models.Model):
    _name = "techv.product.pricelist.line"
    _description= "Pricelist for combo product line"

    mst_id = fields.Many2one('techv.product.pricelist', string="Pricelist")

    product_id = fields.Many2one('product.product')
    image_128 = fields.Image(string="Image")
    inch_feet_type = fields.Selection([
        ('inch', 'Inch'),
        ('feet', 'Feet'),
        ('mm', 'MM'),
        ('basic', 'Basic'),
        ], 'Inch/Feet',default="basic")
    height_length = fields.Float(string="Height/Length")
    width = fields.Float(string="Width")
    sqft = fields.Float(string="Sqft")
    sqft_rate = fields.Float(string="Sqft Rate")
    qty = fields.Float(string="Quantity")
    disc_per = fields.Float(string="Disc%")
    disc_amt = fields.Float(string="Disc Amt")
    price_unit = fields.Float(string="Unit Price")
    amount = fields.Float(string="Amount")
    tax_ids = fields.Many2many('account.tax','ref_pricelist_tax_ids',string="Taxes")
    price_tax = fields.Float(string="Price Tax")
    price_subtotal = fields.Float(string="Tax excl.")
    price_total = fields.Float(string="Tax incl.")
    company_id = fields.Many2one("res.company", string="Company",required=True, default=lambda self: self.env.company.id)
    is_service = fields.Boolean(string='Service',default=False,compute='compute_is_service')

    @api.onchange('product_id','inch_feet_type')
    def onchange_product_id(self):
        for line in self:
            line.image_128 = line.product_id.image_128
            if not line.product_id:
                line.price_unit = 0.0
                line.sqft_rate = 0.0
                self.tax_ids = False
            else:
                line.price_unit = line.product_id.list_price
                self.tax_ids = line.product_id.taxes_id._filter_taxes_by_company(line.company_id)
                if line.inch_feet_type != 'basic':
                    line.sqft_rate = line.product_id.list_price

    @api.onchange('is_service','product_id')
    def compute_is_service(self):
        flg = False
        for service in self:
            if service.product_id.type == 'service':
                flg =  True
            service.is_service = flg
            
    @api.onchange('disc_per')
    def _onchange_disc_per(self):
        sale_per = self.env['ir.config_parameter'].sudo().get_param('saleperson_per')
        # sale_per = self.env.user.dis_per
        sale_per = float(sale_per)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.user_has_groups('sales_team.group_sale_salesman_all_leads') and not self.user_has_groups('sales_team.group_sale_manager'):
            if sale_per and self.disc_per:
                if self.disc_per > sale_per:
                    raise UserError("Not Allowed: Discount exceeds %s%%" % sale_per)
            # if not sale_per:
            #     raise UserError("You are not allowed to give any discount. Please contact your manager.")

    @api.onchange('qty','disc_per','price_unit')
    def _onchange_qty(self):
        self.amount = 0
        if self.qty:
            self.amount = self.qty * self.price_unit

        self.disc_amt = 0
        if self.disc_per:
            self.disc_amt = (self.amount * self.disc_per)/100 

    @api.onchange('tax_ids','qty','price_unit','disc_amt','price_subtotal')
    def _onchange_tax_ids(self):
        self.price_tax = 0 
        if self.tax_ids:
            gst_amt = 0
            for gst in self.tax_ids.children_tax_ids:
                if gst.amount:
                    gst_amt += (self.price_subtotal * gst.amount)/100
            self.price_tax = gst_amt
            
    @api.onchange('inch_feet_type','height_length','width','qty','sqft')
    def onchange_inch_feet_type(self):
        if self.inch_feet_type != 'basic':
            if self.inch_feet_type == 'feet':
                self.sqft = round(self.height_length * self.width, 2)

            if self.inch_feet_type == 'inch':
                length_feet = self.height_length / 12.0
                width_feet = self.width / 12.0
                self.sqft = round(length_feet * width_feet, 2)

            if self.inch_feet_type == 'mm':
                length_feet = self.height_length / 305.0
                width_feet = self.width / 305.0
                self.sqft = round(length_feet * width_feet, 2)
            self.price_unit = self.sqft_rate * self.sqft

    @api.onchange('sqft_rate')
    def _onchange_sqft_rate(self):
        if self.inch_feet_type != 'basic':
            if self.sqft_rate:
                self.price_unit = self.sqft_rate * self.sqft
    
        
    @api.depends('price_subtotal','amount','price_total','price_unit','tax_ids')
    @api.onchange('amount','disc_amt','price_tax','price_unit','tax_ids')
    def _onchange_price_subtotal(self):
        self.price_subtotal = self.amount - self.disc_amt
        self.price_total = self.price_subtotal + self.price_tax