from odoo import api, fields, models,_
from odoo.exceptions import UserError

class ReservedStock(models.Model):
    _name = "reserved.stock"
    _description= "Reserved Stock"

    account_id = fields.Many2one('account.move',string='Account Move')
    pi_chr = fields.Char(string='PI Number')
    user_id = fields.Many2one('res.users',string='Salesperson')
    product_id = fields.Many2one('product.product',string='Product')
    reserved_qty = fields.Float(string='Reserved Qty')
    reserved_type = fields.Selection([('reserved', 'Reserved'),('unreserved', 'Unreserved')], string='Reservation Status')

    def action_unreserved_qty(self):
        data_rec = self.sudo().search([('id','in',self._context.get('active_ids', []))])
        for line in data_rec:
            line.sudo().write({'reserved_type':'unreserved'})

