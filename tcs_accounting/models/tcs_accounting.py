from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    tcs_amounts = fields.Float(string='TCS')
    tds_amt = fields.Float(string='TDS', compute='tds_value_calculation', store=True)
    tcs_percentage = fields.Float(string='TCS Percentage', related='partner_id.tcs_percentage')
    tds_percentage = fields.Float(string='TDS Percentage', related='partner_id.tds_percentage')
    tcs_credit_amts = fields.Float(string=' TCS', compute='net_amount')
    net_amounts = fields.Float(string='Net Amount', compute='net_amount')
    tds_sec = fields.Many2one('tds.accounting', string='TDS section')
    tcs_sec = fields.Many2one('tds.accounting', string='TCS section')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super(AccountMove, self)._onchange_partner_id()
        self.tds_sec = self.partner_id.tds_sec.id
        self.tcs_sec = self.partner_id.tcs_sec.id
        return res

    # TDS Amount ADD IN Order Line
    @api.depends('amount_untaxed', 'partner_id', 'partner_id.tds_applicable', 'tax_totals')
    def tds_value_calculation(self):
        for record in self:
            record.tds_amt = 0.0
            if record.move_type == 'in_invoice':
                if record.partner_id.tds_applicable:
                    if record.partner_id.tds_percentage and isinstance(record.tax_totals, dict) and 'amount_untaxed' in record.tax_totals:
                        record.tds_amt = (record.tax_totals['amount_untaxed'] * record.partner_id.tds_percentage) / 100.0

    # TCS CALCULATION:
    @api.depends('amount_untaxed', 'partner_id', 'partner_id.tcs_percentage','tax_totals')
    def tcs_value_calculation(self):
        for record in self:
            record.tcs_credit_amts = 0.0
            if record.move_type == 'out_invoice':
                if record.partner_id and record.partner_id.tds_applicable:
                    if record.partner_id.tcs_percentage:
                        record.tcs_credit_amts = (record.tax_totals['amount_untaxed'] * record.partner_id.tcs_percentage) / 100
                
    @api.depends('amount_total', 'tds_amt', 'tcs_credit_amts', 'amount_untaxed', 'partner_id.tcs_percentage',
                 'partner_id.tds_percentage','tax_totals')
    def net_amount(self):
        for record in self:
            record.tds_amt = 0.0
            record.tcs_credit_amts = 0.0
            if record.move_type == 'in_invoice':
                if record.partner_id and record.partner_id.tds_percentage:
                    if record.partner_id.tds_percentage:
                        record.tds_amt = (record.tax_totals['amount_untaxed'] * record.partner_id.tds_percentage) / 100.0

            if record.move_type == 'out_invoice':
                if record.partner_id and record.partner_id.tcs_percentage:
                    if record.partner_id.tcs_percentage:
                        record.tcs_credit_amts = (record.tax_totals['amount_untaxed'] * record.partner_id.tcs_percentage) / 100.0
            record.net_amounts = record.amount_total - record.tds_amt
            
    def action_post(self):
        self.create_invoices_new()
        self.create_invoices_tds()
        res = super(AccountMove, self).action_post()
        return res

    def create_invoices_new(self):
        if self.partner_id.tcs_applicable and self.move_type == 'out_invoice':
            if not self.tcs_sec.tds_reversal:
                raise ValidationError("Please select a TDS Reversal G/L Account in the TCS section.")
            line_vals = []
            vals = {
                'account_id': self.tcs_sec.tds_reversal.id,
                'name': 'TCS Amount',
                'debit': self.tcs_credit_amts,
                'display_type': 'tax',
                'price_unit': 1,
            }
            line_vals.append((0, 0, vals))
            for line in self.invoice_line_ids:
                if line.name == 'TCS Amount':
                    line.write(vals)
            xx = self.write({'invoice_line_ids': line_vals})

    def create_invoices_tds(self):
        if self.partner_id.tds_applicable and self.move_type == 'in_invoice':
            if not self.tds_sec.tds_payable:
                raise ValidationError("Please select a TDS Payable G/L Account in the TDS section.")
            line_vals = []
            vals = {
                'account_id': self.tds_sec.tds_payable.id,
                'name': 'TDS Amount',
                'credit': self.tds_amt,
                'display_type': 'tax',
                'price_unit': 1,
            }
            line_vals.append((0, 0, vals))
            for line in self.line_ids:
                if line.name == 'TDS Amount':
                    line.write(vals)
            xx = self.write({'line_ids': line_vals})
