from odoo import models, fields, api
from datetime import datetime, timedelta, date
from num2words import num2words
import re
from odoo.exceptions import UserError, ValidationError
    
class InheritAccountLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('product_id')
    def onchange_gst_product(self):
        for line in self:
            # Exit if there's no product or the product has no default taxes
            if not line.product_id or not line.product_id.taxes_id:
                continue

            # For "Deemed Export", always apply a specific tax and stop
            if line.move_id.l10n_in_gst_treatment == 'deemed_export':
                gst_rec = self.env['account.tax'].sudo().search([('name', '=', '0.10% IGST'), ('type_tax_use', '=', 'sale')], limit=1)
                if gst_rec:
                    line.tax_ids = gst_rec
                continue # Stop further processing

            # For Interstate sales (different state)
            if line.move_id.partner_id.state_id and line.company_id.state_id and line.move_id.partner_id.state_id != line.company_id.state_id:
                # Assumes the first tax on the product is the one to be mapped
                product_tax = line.product_id.taxes_id[0]
                gst_rec = self.env['account.tax'].sudo().search([
                    ('amount', '=', product_tax.amount),
                    ('type_tax_use', '=', 'sale'),
                    ('tax_group_id.name', '=', 'IGST')
                ], limit=1)
                
                if gst_rec:
                    line.tax_ids = gst_rec
                else:
                    # If no corresponding IGST is found, clear the tax
                    line.tax_ids = False
            else:
                # For Intrastate sales (same state), just use the product's default taxes
                line.tax_ids = line.product_id.taxes_id