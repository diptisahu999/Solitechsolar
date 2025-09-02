from odoo import models, fields, api
from lxml import etree

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    saleperson_per = fields.Float(string="Discount Percentage For Saleperson",config_parameter = 'saleperson_per')
    invperson_per = fields.Float(string="Discount Percentage For Invoiceperson",config_parameter = 'invperson_per')
    
