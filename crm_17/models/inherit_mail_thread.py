from odoo import models, fields, api
from datetime import datetime, timedelta, date
from markupsafe import Markup
from odoo import _, api, exceptions, fields, models, tools, registry, SUPERUSER_ID, Command
from odoo.tools.misc import clean_context, split_every


class InheritMailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_create(self, values_list):
        """ Low-level helper to create mail.message records. It is mainly used
        to hide the cleanup of given values, for mail gateway or helpers."""
        create_values_list = []

        # preliminary value safety check
        self._raise_for_invalid_parameters(
            {key for values in values_list for key in values.keys()},
            restricting_names=self._get_message_create_valid_field_names()
        )
        is_internal_user = self.env.user.has_group('base.group_user')
        for values in values_list:
            create_values = dict(values)
            # Avoid warnings about non-existing fields
            for x in ('from', 'to', 'cc'):
                create_values.pop(x, None)

            # Apply green font style if message_type is 'comment'
            if is_internal_user and create_values.get('message_type') == 'comment' and create_values.get('body'):
                original_body = str(create_values['body'])
                styled_body = f'<span style="color:green; font-weight:bold;">{original_body}</span>'
                create_values['body'] = Markup(styled_body)

            create_values['partner_ids'] = [Command.link(pid) for pid in (create_values.get('partner_ids') or [])]
            create_values_list.append(create_values)

        return self.env['mail.message'].with_context(
            clean_context(self.env.context)
        ).create(create_values_list)
    
    def _message_auto_subscribe_notify(self, partner_ids, template):
        """ Notify new followers, using a template to render the content of the
        notification message. Notifications pushed are done using the standard
        notification mechanism in mail.thread. It is either inbox either email
        depending on the partner state: no user (email, customer), share user
        (email, customer) or classic user (notification_type)

        :param partner_ids: IDs of partner to notify;
        :param template: XML ID of template used for the notification;
        """
        return
    
    def _notify_thread_by_email(self, message, recipients_data, msg_vals=False,
                                mail_auto_delete=True,  # mail.mail
                                model_description=False, force_email_company=False, force_email_lang=False,  # rendering
                                subtitles=None,  # rendering
                                resend_existing=False, force_send=True, send_after_commit=True,  # email send
                                 **kwargs):
        
        if message.subtype_id == self.env.ref('mail.mt_note'):
            return True  # Don't send emails

        return super()._notify_thread_by_email(message, recipients_data, msg_vals=False,
                                mail_auto_delete=True,  # mail.mail
                                model_description=False, force_email_company=False, force_email_lang=False,  # rendering
                                subtitles=None,  # rendering
                                resend_existing=False, force_send=True, send_after_commit=True,  # email send
                                 **kwargs)
    
class InheritMailMessage(models.AbstractModel):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, values_list):
        messages = super().create(values_list)

        for message in messages:
            if (message.model == 'sale.order' and message.message_type == 'comment' and message.res_id):
                sale_order = self.env["sale.order"].browse(message.res_id)
                if sale_order.opportunity_id:
                    sale_order_number = sale_order.name or 'Sale Order'
                    # Compose formatted message body with inline styling
                    formatted_body = (
                        f"<b>{sale_order_number}:</b> "
                        f"<span style='color:green; font-weight:bold'>{message.body}</span>"
                    )
                    sale_order.opportunity_id.message_post(
                        body=Markup(formatted_body),
                        subtype_id=self.env.ref('mail.mt_note').id,  # Ensure it's an internal note
                    )

        return messages