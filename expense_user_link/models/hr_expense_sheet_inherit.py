# -*- coding: utf-8 -*-
# 1. ADD THESE THREE LINES AT THE TOP
import traceback
import logging
_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrExpenseSheetInherit(models.Model):
    _inherit = 'hr.expense.sheet'

    # ... (all your fields like is_paid_manually, etc. are here, no changes needed) ...
    is_paid_manually = fields.Boolean(
        string='Paid (manual)',
        default=False,
        help="Checked when the expense was paid outside accounting (manually marked)."
    )
    paid_by_user_id = fields.Many2one(
        'res.users',
        string='Marked Paid By',
        readonly=True,
    )
    paid_date = fields.Datetime(
        string='Marked Paid On',
        readonly=True,
    )


    @api.model
    def _ensure_user_can_mark_paid(self):
        return self.env.user.has_group('base.group_system') or \
               self.env.user.has_group('hr_expense.group_hr_expense_manager')

    def action_mark_as_paid(self):
        # 2. ADD THESE THREE LINES INSIDE THE FUNCTION
        _logger.error("--- UNEXPECTED CALL TO action_mark_as_paid ---")
        _logger.error("--- STACK TRACE TO FIND THE CULPRIT: ---")
        traceback.print_stack()

        """Mark the sheet and its lines as paid without creating accounting moves."""
        if not self._ensure_user_can_mark_paid():
            raise UserError(_("You are not allowed to mark expense as paid."))

        for sheet in self:
            # ... (the rest of your function code is here, no changes needed) ...
            if sheet.state != 'approve':
                 raise UserError(_("You can only mark an expense as paid when it is in the 'Approved' state."))

            if sheet.expense_line_ids:
                sheet.expense_line_ids.sudo().write({'state': 'done'})

            sheet.state = 'done'

            sheet.is_paid_manually = True
            sheet.paid_by_user_id = self.env.uid
            sheet.paid_date = fields.Datetime.now()

        return True