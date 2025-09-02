from odoo import api, fields, models,_
from num2words import num2words

class LabelMaster(models.Model):
    _name = "label.mst"
    _description= "Label Master"

    name = fields.Char(string='Name')