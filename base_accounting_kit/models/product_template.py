# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    upstock_qty = fields.Float(string='Upcoming Stock', compute='_compute_upstock_qty')

    @api.depends('product_variant_ids', 'product_variant_ids.upcoming_stock_ids')
    def _compute_upstock_qty(self):
        # The key change: iterate over 'self' to process each record.
        for product in self:  
            upcoming_stock = self.env['upcoming.stock'].sudo().search([('product_id', '=', product.id)], order='id desc', limit=1)
            
            if upcoming_stock:
                product.upstock_qty = upcoming_stock.quantity
            else:
                product.upstock_qty = 0
