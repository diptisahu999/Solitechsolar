from odoo import models, api, _, fields
from odoo.exceptions import ValidationError
from odoo.tools import is_html_empty

class MailActivityType(models.Model):
    _inherit = 'mail.activity.type'

    def _auto_init(self):
        res = super()._auto_init()
        # Force keep_done = True for all existing activity types so done activities show up on page
        self.env.cr.execute("UPDATE mail_activity_type SET keep_done = True WHERE keep_done = False")
        return res

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    done_feedback = fields.Text('Done Feedback')

    def _action_done(self, feedback=False, attachment_ids=None):
        if feedback:
            self.write({'done_feedback': feedback})
        return super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def action_feedback(self, feedback=False, attachment_ids=None):
        if not feedback or is_html_empty(feedback):
            # If done from wizard (quick update), check if note or summary is filled
            if self.env.context.get('mail_activity_quick_update'):
                if not is_html_empty(self.note):
                    feedback = self.note
                elif self.summary:
                    feedback = self.summary
                else:
                    raise ValidationError(_("Please write your notes or summary before marking this activity as Done."))
            else:
                raise ValidationError(_("Feedback is required. Please write feedback before marking this activity as Done."))
        return super(MailActivity, self).action_feedback(feedback=feedback, attachment_ids=attachment_ids)

    def action_feedback_schedule_next(self, feedback=False, attachment_ids=None):
        if not feedback or is_html_empty(feedback):
            if self.env.context.get('mail_activity_quick_update'):
                if not is_html_empty(self.note):
                    feedback = self.note
                elif self.summary:
                    feedback = self.summary
                else:
                    raise ValidationError(_("Please write your notes or summary before scheduling the next activity."))
            else:
                raise ValidationError(_("Feedback is required. Please write feedback before scheduling the next activity."))
        return super(MailActivity, self).action_feedback_schedule_next(feedback=feedback, attachment_ids=attachment_ids)
