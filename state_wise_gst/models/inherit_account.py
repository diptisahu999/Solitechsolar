from odoo import models, fields, api
from datetime import datetime, timedelta, date
from num2words import num2words
import re
from odoo.exceptions import UserError, ValidationError
    
class InheritAccountLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('product_id')
    def onchange_gst_product(self):
    	# for line in self:
        for line in self:
            if line.product_id.taxes_id:
                for gst in line.product_id.taxes_id:

                    if line.move_id.l10n_in_gst_treatment == 'deemed_export':
                        gst_recs = self.env['account.tax'].sudo().search([('name', '=', '0.10% GST'),('type_tax_use', '=', 'sale')])
                        if gst_recs:
                            line.tax_ids = [(6, 0, gst_recs.ids)] 

                    if line.move_id.partner_id.state_id.name != line.company_id.state_id.name:
                        gst_rec = self.env['account.tax'].sudo().search([('amount','=',gst.amount),('type_tax_use','=','sale'),('tax_group_id.name','=','IGST')],limit=1)
                        line.tax_ids = [(6,0,[gst_rec.id])]

                        if line.move_id.l10n_in_gst_treatment == 'deemed_export':
                            gst_rec = self.env['account.tax'].sudo().search([('name', '=', '0.10% IGST'),('type_tax_use', '=', 'sale')], limit=1)
                            if gst_rec:
                                line.tax_ids = [(6, 0, [gst_rec.id])]