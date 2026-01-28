from odoo import models, fields, api
from lxml import etree

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    saleperson_per = fields.Float(string="Discount Percentage For Saleperson",config_parameter = 'saleperson_per')
    invperson_per = fields.Float(string="Discount Percentage For Invoiceperson",config_parameter = 'invperson_per')

    global_dcr_rate = fields.Float(string="Global DCR Price", config_parameter='crm_17.global_dcr_rate')
    global_non_dcr_rate = fields.Float(string="Global NON-DCR Price", config_parameter='crm_17.global_non_dcr_rate')
    
    global_min_unit_price = fields.Float(string="Global Non-DCR Min Unit Price", config_parameter='crm_17.global_min_unit_price')
    global_dcr_min_unit_price = fields.Float(string="Global DCR Min Unit Price", config_parameter='crm_17.global_dcr_min_unit_price')

    def action_apply_global_prices(self):
        self.ensure_one()
        # Check permissions
        if not self.env.user.has_group('crm_17.group_global_price_update'):
             from odoo.exceptions import AccessError
             raise AccessError("You do not have permission to update global prices.")
             
        products = self.env['product.template'].search([])
        vals = {}
        if self.global_dcr_rate > 0:
            vals['dcr_rate'] = self.global_dcr_rate
        if self.global_non_dcr_rate > 0:
            vals['non_dcr_rate'] = self.global_non_dcr_rate
        if self.global_min_unit_price > 0:
            vals['min_unit_price_watt'] = self.global_min_unit_price
        if self.global_dcr_min_unit_price > 0:
            vals['dcr_min_unit_price_watt'] = self.global_dcr_min_unit_price
            
        if vals:
             products.write(vals)
