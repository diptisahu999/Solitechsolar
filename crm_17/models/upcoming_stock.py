from odoo import api, fields, models,_
from odoo.exceptions import UserError

class UpcomingStock(models.Model):
    _name = "upcoming.stock"
    _description= "Upcoming Stock"
    _inherit = ['mail.thread']
    _rec_name = "product_id"

    date = fields.Date(string='Schedule Date',tracking=True)
    contener_no = fields.Char(string="Container No.",tracking=True)
    product_id = fields.Many2one('product.product',tracking=True)
    qty = fields.Float(string="Quantity",tracking=True)
