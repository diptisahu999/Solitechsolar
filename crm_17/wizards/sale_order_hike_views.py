# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderHike(models.TransientModel):
    _name = 'sale.order.hike'
    _description = "Hike And Qty Wizard"

    sale_order_id = fields.Many2one('sale.order', default=lambda self: self.env.context.get('active_id'), required=True)
    company_id = fields.Many2one(related='sale_order_id.company_id')
    currency_id = fields.Many2one(related='sale_order_id.currency_id')
    hike = fields.Integer(string="Hike",store=True)
    qty = fields.Integer(string="Qty",store=True)
    hike_type = fields.Selection(selection=[('hike', "hike"),
                                            ('qty', "qty")])

    def action_apply_hike_qty(self):
        self = self.with_company(self.company_id)
        if self.hike_type == 'hike':
            for line in self.sale_order_id.order_line.filtered(lambda x: x.product_id.type == 'product'):
                if line.inch_feet_type == 'basic':
                    if line.price_unit > 0 and self.hike:
                        extra_price = (line.price_unit * self.hike) / 100
                        line.write({'price_unit': (line.price_unit +  extra_price)})
                if line.inch_feet_type != 'basic':
                    if line.sqft_rate > 0 and self.hike:
                        extra_sqft_rate = (line.sqft_rate * self.hike) / 100
                        line.write({'sqft_rate': (line.sqft_rate +  extra_sqft_rate)})
                        line.onchange_inch_feet_type()

        if self.hike_type == 'qty':
            for line in self.sale_order_id.order_line.filtered(lambda x: x.product_id.type == 'product'):
                if line.inch_feet_type == 'basic':
                    line.write({'product_uom_qty': self.qty})

