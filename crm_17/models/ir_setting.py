from odoo import models, fields, api
from lxml import etree

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    saleperson_per = fields.Float(string="Discount Percentage For Saleperson",config_parameter = 'saleperson_per')
    invperson_per = fields.Float(string="Discount Percentage For Invoiceperson",config_parameter = 'invperson_per')

    global_dcr_rate = fields.Float(string="Global DCR Price", config_parameter='crm_17.global_dcr_rate')
    global_non_dcr_rate = fields.Float(string="Global NON-DCR Price", config_parameter='crm_17.global_non_dcr_rate')

    def action_apply_global_prices(self):
        self.ensure_one()
        products = self.env['product.template'].search([])
        products.write({
            'dcr_rate': self.global_dcr_rate,
            'non_dcr_rate': self.global_non_dcr_rate,
        })
