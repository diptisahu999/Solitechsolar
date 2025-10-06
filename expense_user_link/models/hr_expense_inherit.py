# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class HrExpenseInherit(models.Model):
    _inherit = 'hr.expense'

    paid_by_user_id = fields.Many2one(
        'res.users',
        string='Paid By',
        tracking=True,
        domain=[('share', '=', False)]
    )
    is_current_user_approver = fields.Boolean(
        string="Is Current User an Approver",
        compute='_compute_is_current_user_approver'
    )

    def _compute_is_current_user_approver(self):
        is_approver = self.env.user.has_group('hr_expense.group_hr_expense_manager')
        for expense in self:
            expense.is_current_user_approver = is_approver

    @api.onchange('paid_by_user_id')
    def _onchange_paid_by_user_id(self):
        if self.paid_by_user_id:
            user_as_sudo = self.paid_by_user_id.sudo()
            if not user_as_sudo.employee_id:
                raise UserError(_("The selected user '%s' is not linked to an employee record.") % self.paid_by_user_id.name)
            self.employee_id = user_as_sudo.employee_id
        else:
            self.employee_id = False

    @api.model
    def default_get(self, fields_list):
        res = super(HrExpenseInherit, self).default_get(fields_list)
        if 'paid_by_user_id' in fields_list:
            res['paid_by_user_id'] = self.env.uid
        if 'employee_id' in fields_list:
            current_employee = self.env.user.employee_id
            if current_employee:
                res['employee_id'] = current_employee.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            is_approver = self.env.user.has_group('hr_expense.group_hr_expense_manager')
            paid_by_user_id = vals.get('paid_by_user_id', self.env.uid)
            if not is_approver and paid_by_user_id != self.env.uid:
                raise ValidationError(_("You are not allowed to create an expense on behalf of another user."))
            if paid_by_user_id and not vals.get('employee_id'):
                user = self.env['res.users'].browse(paid_by_user_id).sudo()
                if not user.employee_id:
                    raise UserError(_("The selected user '%s' is not linked to an employee record.") % user.name)
                vals['employee_id'] = user.employee_id.id
        return super(HrExpenseInherit, self).create(vals_list)

    def write(self, vals):
        if 'paid_by_user_id' in vals:
            is_approver = self.env.user.has_group('hr_expense.group_hr_expense_manager')
            if not is_approver and vals['paid_by_user_id'] != self.env.uid:
                 raise ValidationError(_("You are not allowed to change the user of an expense."))
            user = self.env['res.users'].browse(vals['paid_by_user_id']).sudo()
            if not user.employee_id:
                raise UserError(_("The selected user '%s' is not linked to an employee record.") % user.name)
            vals['employee_id'] = user.employee_id.id
        return super(HrExpenseInherit, self).write(vals)