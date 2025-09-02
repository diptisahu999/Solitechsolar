from odoo import api, fields, models,_

class InheritRepairOrder(models.Model):
    _inherit = "repair.order"

    product_type = fields.Selection([('old', 'Old'),('new', 'New')], string='Product Type',default='new')
    is_serial_gen = fields.Boolean(string="Serial Genrate")

    @api.onchange('product_type')
    def _onchange_product_type(self):
        if self.product_type == 'old':
            self.lot_id = False

    def action_old_product_serial_genrate(self):
        last_part = self.name.split('/')[-1]
        serial_name = self.product_id.barcode + last_part
        return {
            'type': 'ir.actions.act_window',
            'name': 'Old Product Serial Genrate',
            'view_mode': 'form',
            'res_model': 'old.product.serial.wiz',
            'target':'new',
            'context':{'default_serial_name':serial_name}
        }

    def action_sale_order_repair_wiz_open(self):
        vals = {"model":'repair.order','ids':self.ids}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Quotations',
            'view_mode': 'form',
            'res_model': 'sale.order.repair.wiz',
            'target':'new',
            'context':vals
        }
    
    def action_create_sale_order(self):
        res = super(InheritRepairOrder, self).action_create_sale_order()
        sale_order = self.env['sale.order'].search([('repair_order_ids', 'in', self.id)])
        if sale_order:
            for line in sale_order.order_line:
                line.onchange_sake_product_image()
        return res