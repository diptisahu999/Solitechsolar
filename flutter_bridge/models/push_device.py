from odoo import models, fields

class PushDevice(models.Model):
    _name = 'push.device'
    _description = 'Push Notification Device'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    fcm_token = fields.Char(string='FCM Token', required=True)
    platform = fields.Selection(
        [('android', 'Android'), ('ios', 'iOS')],
        required=True
    )
    active = fields.Boolean(default=True)
