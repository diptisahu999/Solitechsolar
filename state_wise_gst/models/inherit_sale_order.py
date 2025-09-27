from odoo import api, fields, models,_
from num2words import num2words
import re
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, float_round, format_date, groupby

class InheritSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_id')
    def onchange_gst_product(self):
        for line in self:
            if not line.product_id:
                continue

            # Default to the product's taxes (for intrastate)
            taxes = line.product_id.taxes_id

            # For Interstate sales (partner state is different from company state)
            partner = line.order_id.partner_id
            company = line.order_id.company_id
            if partner.state_id and company.state_id and partner.state_id != company.state_id:
                # Find a matching IGST tax if the product has a default tax
                if line.product_id.taxes_id:
                    # Get the rate from the first default tax on the product
                    tax_rate = line.product_id.taxes_id[0].amount
                    
                    igst_tax = self.env['account.tax'].search([
                        ('amount', '=', tax_rate),
                        ('type_tax_use', '=', 'sale'),
                        ('company_id', '=', company.id),
                        ('tax_group_id.name', '=', 'IGST')
                    ], limit=1)
                    
                    # If an IGST tax is found, use it. Otherwise, clear the taxes.
                    taxes = igst_tax if igst_tax else False

            line.tax_id = taxes
                                