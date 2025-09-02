from odoo import fields, models, api, _


class TdsAccounting(models.Model):
    _name = 'tds.accounting'
    _description = 'Tds Accounting'

    name = fields.Char(string='Name')
    nature_of_payment = fields.Char(string='Nature Of Payment')
    tds_reversal = fields.Many2one('account.account', string='TDS Reversal G/L Account')
    tds_payable = fields.Many2one('account.account', string='TDS Payable G/L Account')
    company = fields.Char(string='Company')
    companies = fields.Char(string='Companies')
    individual_huf = fields.Float(string='Individual /HUF %')
    no_pan = fields.Float(string='No Pan %')
