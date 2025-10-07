# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrExpenseSheetInherit(models.Model):
    _inherit = 'hr.expense.sheet'

    # The Boolean is replaced by a Selection field for a complete status
    manual_payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('paid', 'Paid Manually'),
    ], string="Manual Payment Status", default='not_paid', tracking=True)
    
    paid_by_user_id = fields.Many2one(
        'res.users',
        string='Marked Paid By',
        readonly=True,
        tracking=True,
    )
    paid_date = fields.Datetime(
        string='Marked Paid On',
        readonly=True,
        tracking=True,
    )

    @api.model
    def _ensure_user_can_change_payment_state(self):
        """Return True if current user is allowed to mark as paid/unpaid."""
        return self.env.user.has_group('base.group_system') or \
               self.env.user.has_group('hr_expense.group_hr_expense_manager')

    def action_mark_as_paid(self):
        """Sets the custom payment status to 'Paid Manually'."""
        if not self._ensure_user_can_change_payment_state():
            raise UserError(_("You are not allowed to change the payment status of an expense."))

        for sheet in self.filtered(lambda s: s.state == 'approve'):
            sheet.write({
                'manual_payment_state': 'paid',
                'paid_by_user_id': self.env.uid,
                'paid_date': fields.Datetime.now()
            })
        return True

    def action_mark_as_unpaid(self):
        """Resets the custom payment status to 'Not Paid'."""
        if not self._ensure_user_can_change_payment_state():
            raise UserError(_("You are not allowed to change the payment status of an expense."))

        for sheet in self:
            sheet.write({
                'manual_payment_state': 'not_paid',
                'paid_by_user_id': False,
                'paid_date': False
            })
        return True