from odoo import models, fields

class Users(models.Model):
    _inherit = "res.users"
    fcm_token = fields.Char("FCM Token")
