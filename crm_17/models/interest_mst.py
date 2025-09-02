from odoo import api, fields, models,_
from num2words import num2words

class InterestMaster(models.Model):
    _name = "interest.mst"
    _description= "Interest Master"

    name = fields.Char(string='Name')