from odoo import api, fields, models,_

class CourierMater(models.Model):
    _name = "courier.mst"
    _description= "Courier Mater"

    name = fields.Char(string='Name')