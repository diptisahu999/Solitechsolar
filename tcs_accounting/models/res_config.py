from odoo import fields, models, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    roundoff_account_id = fields.Many2one('account.account', string='Round off Account')
    tcs_account_id = fields.Many2one(related='company_id.tcs_act_id', string='TCS Account', readonly=False)
    tcs_account_id = fields.Many2one(related='company_id.tcs_act_id', string='TCS Account', readonly=False)
    tds_account_id = fields.Many2one(related='company_id.tds_act_id', string='TDS Account', readonly=False)

class ResCompany(models.Model):
    _inherit = 'res.company'

    tcs_act_id = fields.Many2one('account.account', string='TCS Account')
    tds_act_id = fields.Many2one('account.account', string='TDS Account')