from odoo import api, fields, models,_
from num2words import num2words
import re
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, float_round, format_date, groupby

class InheritSaleOrder(models.Model):
    _inherit = "sale.order"

    exchange_rate = fields.Float("Exchange Rate")

class InheritSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_exchange_rate = fields.Boolean(string='Is Exchange Rate',default=False,compute='_compute_exchange_rate_price_unit')

    @api.depends('product_id', 'product_uom', 'order_id.exchange_rate', 'inch_feet_type')
    def _compute_exchange_rate_price_unit(self):
        for line in self:
            flg = False  # Default value for is_exchange_rate
            if line.order_id.exchange_rate > 0:
                if line.inch_feet_type == 'basic' and line.product_id:
                    line = line.with_company(line.company_id)
                    price = line._get_display_price()
                    if line.price_unit == 0:
                        line.price_unit = line.product_id._get_tax_included_unit_price(
                            line.company_id or line.env.company,
                            line.order_id.currency_id,
                            line.order_id.date_order,
                            'sale',
                            fiscal_position=line.order_id.fiscal_position_id,
                            product_price_unit=price,
                            product_currency=line.currency_id
                        ) / line.order_id.exchange_rate
                    flg = True
            else:
                if line.inch_feet_type == 'basic' and line.product_id:
                    line = line.with_company(line.company_id)
                    price = line._get_display_price()
                    if line.price_unit == 0:
                        line.price_unit = line.product_id._get_tax_included_unit_price(
                            line.company_id or line.env.company,
                            line.order_id.currency_id,
                            line.order_id.date_order,
                            'sale',
                            fiscal_position=line.order_id.fiscal_position_id,
                            product_price_unit=price,
                            product_currency=line.currency_id
                        )
            line.is_exchange_rate = flg

