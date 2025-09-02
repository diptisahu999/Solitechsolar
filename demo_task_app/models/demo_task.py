from odoo import models, fields, api
from datetime import date, timedelta

class DemoTask(models.Model):
    _name = 'demo.task'
    _description = 'Demo Task for Notifications'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Task Name", required=True)
    description = fields.Text(string="Description")
    user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)
    manager_id = fields.Many2one('res.users', string='Manager', tracking=True)
    deadline = fields.Date(string='Deadline', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High')
    ], string='Priority', default='0', tracking=True)
    state = fields.Selection([
        ('new', 'New'),
        ('done', 'Done'),
    ], string='Status', default='new', tracking=True)

    def _get_all_followers(self):
        """Helper to get all users following the task."""
        user_ids = set()
        for follower in self.message_follower_ids:
            user = self.env['res.users'].search([('partner_id', '=', follower.partner_id.id)], limit=1)
            if user:
                user_ids.add(user.id)
        return list(user_ids)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.user_id:
                users_to_notify = record._get_all_followers()
                self.env['notification.manager'].send_push_notification(
                    user_ids=users_to_notify,
                    title="New Task Created & Assigned",
                    message=f"Task '{record.name}' was assigned to {record.user_id.name}."
                )
        return records

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            # --- Scenario 1: Task is re-assigned ---
            if 'user_id' in vals and vals.get('user_id'):
                # THE FIX: Automatically subscribe the new user as a follower.
                # This grants them access to the record and its chatter.
                record.message_subscribe(partner_ids=[record.user_id.partner_id.id])

                users_to_notify = record._get_all_followers()
                self.env['notification.manager'].send_push_notification(
                    user_ids=users_to_notify,
                    title="Task Re-Assigned",
                    message=f"Task '{record.name}' has been assigned to {record.user_id.name}."
                )
            
            # --- Scenario 2: Task is marked as Done ---
            if 'state' in vals and vals['state'] == 'done':
                users_to_notify = set()
                if record.manager_id:
                    users_to_notify.add(record.manager_id.id)
                if record.create_uid: # create_uid is the original creator
                    users_to_notify.add(record.create_uid.id)
                
                if users_to_notify:
                    self.env['notification.manager'].send_push_notification(
                        user_ids=list(users_to_notify),
                        title="Task Completed",
                        message=f"The task '{record.name}' has been marked as done.",
                        notification_type='success' # Use a green banner
                    )

            # --- Scenario 3: Priority is raised to High ---
            if 'priority' in vals and vals['priority'] == '2':
                if record.user_id:
                    self.env['notification.manager'].send_push_notification(
                        user_ids=[record.user_id.id],
                        title="High Priority Task",
                        message=f"The task '{record.name}' has been marked as high priority.",
                        notification_type='warning' # Use a yellow banner
                    )
        return res

    @api.model
    def _cron_send_deadline_reminders(self):
        """
        Scheduled Action: Sends a reminder for tasks due tomorrow.
        """
        tomorrow = date.today() + timedelta(days=1)
        tasks_due_tomorrow = self.search([
            ('deadline', '=', tomorrow),
            ('state', '=', 'new'),
            ('user_id', '!=', False)
        ])

        for task in tasks_due_tomorrow:
            self.env['notification.manager'].send_push_notification(
                user_ids=[task.user_id.id],
                title="Deadline Reminder",
                message=f"The task '{task.name}' is due tomorrow.",
                notification_type='danger' # Use a red banner
            )
