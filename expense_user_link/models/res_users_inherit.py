# -*- coding: utf-8 -*-
from odoo import models, api, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class UsersInherit(models.Model):
    _inherit = 'res.users'

    def _create_missing_employees_for_existing_users(self):
        _logger.info("Starting check for existing users missing an employee record...")
        admin_employee = self.env['hr.employee'].sudo().search([('user_id', '=', SUPERUSER_ID)], limit=1)
        users_to_fix = self.env['res.users'].search([('share', '=', False), ('employee_id', '=', False)])
        if not users_to_fix:
            _logger.info("No users found that need a new employee record created.")
            return
        _logger.info(f"Found {len(users_to_fix)} users to fix. Creating employee records now...")
        for user in users_to_fix:
            employee_vals = {
                'name': user.name, 'user_id': user.id,
                'company_id': user.company_id.id or self.env.company.id,
                'parent_id': admin_employee.id if admin_employee else False,
            }
            self.env['hr.employee'].sudo().create(employee_vals)
            _logger.info(f"Created employee record for user '{user.name}'.")
        _logger.info("Finished creating missing employee records.")

    @api.model_create_multi
    def create(self, vals_list):
        new_users = super(UsersInherit, self).create(vals_list)
        admin_employee = self.env['hr.employee'].sudo().search([('user_id', '=', SUPERUSER_ID)], limit=1)
        for user in new_users:
            if not user.share:
                if not user.employee_id:
                    employee_vals = {
                        'name': user.name, 'user_id': user.id,
                        'company_id': user.company_id.id or self.env.company.id,
                        'parent_id': admin_employee.id if admin_employee else False,
                    }
                    self.env['hr.employee'].sudo().create(employee_vals)
        return new_users