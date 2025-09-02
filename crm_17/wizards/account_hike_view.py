# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveHike(models.TransientModel):
    _name = 'account.move.hike'
    _description = "Hike And Qty Wizard"

    account_move_id = fields.Many2one('account.move', default=lambda self: self.env.context.get('active_id'), required=True)
    company_id = fields.Many2one(related='account_move_id.company_id')
    currency_id = fields.Many2one(related='account_move_id.currency_id')
    hike = fields.Integer(string="Hike",store=True)
    qty = fields.Integer(string="Qty",store=True)
    hike_type = fields.Selection(selection=[('hike', "hike"),
                                            ('qty', "qty")])

    def action_apply_hike_qty(self):
        self = self.with_company(self.company_id)
        if self.hike_type == 'hike':
            for line in self.account_move_id.invoice_line_ids:
                if line.inch_feet_type == 'basic':
                    if line.price_unit > 0 and self.hike > 0:
                        extra_price = (line.price_unit * self.hike) / 100
                        line.write({'price_unit': (line.price_unit +  extra_price)})

        if self.hike_type == 'qty':
            for line in self.account_move_id.invoice_line_ids:
                if line.inch_feet_type == 'basic':
                    line.write({'quantity': self.qty})

class AccountMoveValidation(models.TransientModel):
    _name = 'account.move.validation'
    _description = "Account Move Validation"

    name = fields.Html(string='Name')

