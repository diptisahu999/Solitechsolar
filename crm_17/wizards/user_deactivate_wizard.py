# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class UserDeactivateWizard(models.TransientModel):
    _name = 'user.deactivate.wizard'
    _description = 'User Deactivate Wizard'

    user_id = fields.Many2one('res.users', string='User', required=True, readonly=True)
    user_name = fields.Char(string='User Name', readonly=True)
    email = fields.Char(string='Email', readonly=True)
    deactivate = fields.Boolean(string='Deactivate', default=False)

    @api.model
    def default_get(self, fields_list):
        res = super(UserDeactivateWizard, self).default_get(fields_list)
        # Automatically fetch the current logged-in user
        current_user = self.env.user
        if 'user_id' in fields_list:
            res['user_id'] = current_user.id
        if 'user_name' in fields_list:
            res['user_name'] = current_user.name or ''
        if 'email' in fields_list:
            res['email'] = current_user.email or ''
        return res

    def action_yes(self):
        """Action when user clicks Yes - Archive the user"""
        self.ensure_one()
        user = self.user_id

        if not user:
            raise UserError(_("No user selected."))

        # Archive the user (set active = False)
        # Direct SQL is used to bypass Odoo's self-deactivation restriction.
        # This keeps other constraints untouched and avoids the "cannot deactivate current user" error.
        self.env.cr.execute(
            "UPDATE res_users SET active = FALSE WHERE id = %s",
            [user.id],
        )
        user.invalidate_recordset(['active'])
        
        self.deactivate = True
        
        return {
            'type': 'ir.actions.act_window_close',
        }

    def action_no(self):
        """Action when user clicks No"""
        self.deactivate = False
        return {
            'type': 'ir.actions.act_window_close',
        }

