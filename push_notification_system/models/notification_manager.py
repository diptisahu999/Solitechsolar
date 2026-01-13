# from odoo import models, api
# import logging

# _logger = logging.getLogger(__name__)

# class NotificationManager(models.AbstractModel):
#     _name = 'notification.manager'
#     _description = 'Push Notification Manager'

#     def send_push_notification(self, user_ids, title, message, notification_type='info'):
#         """
#         This method prepares the notification payload for Odoo's internal
#         notification service and sends it over the bus.
#         """
#         _logger.info("--- DEBUG: send_push_notification called ---")
#         _logger.info(f"--- DEBUG: Target User IDs: {user_ids} ---")

#         users = self.env['res.users'].browse(user_ids)
#         if not users:
#             _logger.warning("--- DEBUG: No users found for the given IDs. Aborting. ---")
#             return

#         payload = {
#             'title': title,
#             'message': message,
#             'type': notification_type,
#         }
        
#         # Prepare the list of channels to send to
#         channels = [(user.partner_id, 'odoos_notification', payload) for user in users]
#         _logger.info(f"--- DEBUG: Preparing to send to channels: {channels} ---")

#         try:
#             self.env['bus.bus']._sendmany(channels)
#             _logger.info("--- DEBUG: _sendmany command executed successfully. ---")
#         except Exception as e:
#             _logger.error(f"--- DEBUG: Error executing _sendmany: {e} ---")






# from odoo import models
# import logging

# _logger = logging.getLogger(__name__)

# class NotificationManager(models.AbstractModel):
#     _name = 'notification.manager'
#     _description = 'Push Notification Manager'

#     # Optional alias if other code still calls this name
#     def send_push_notification(self, user_ids, title, message, notification_type='info'):
#         _logger.info("--- DEBUG: send_push_notification called ---")
#         _logger.info(f"--- DEBUG: Target User IDs: {user_ids} ---")

#         users = self.env['res.users'].browse(user_ids)
#         if not users:
#             _logger.warning("--- DEBUG: No users found for the given IDs. Aborting. ---")
#             return

#         # Handle if message is dict or string
#         if isinstance(message, dict):
#             styled_message = f"""
#             📌 <b>Lead:</b> {message.get('lead_name', 'Unknown')}<br>
#             🛒 <b>Orders:</b> {message.get('orders', 'None')}<br>
#             🧾 <b>Invoices:</b> {message.get('invoices', 'None')}<br>
#             👤 <b>Assigned to:</b> {message.get('assigned_to', 'Unassigned')}
#             """
#         else:
#             styled_message = message  # Use raw string if message is not dict

#         styled_title = f'🔔 <b>{title}</b>'

#         payload = {
#             'title': styled_title,
#             'message': styled_message,
#             'type': notification_type,
#         }

#         channels = [(user.partner_id, 'odoos_notification', payload) for user in users]

#         try:
#             self.env['bus.bus']._sendmany(channels)
#             _logger.info("--- DEBUG: _sendmany command executed successfully. ---")
#         except Exception as e:
#             _logger.error(f"--- DEBUG: Error executing _sendmany: {e} ---")

#         return self.send_chat_notification(user_ids, styled_title, styled_message)


#     def send_chat_notification(self, user_ids, title, message):
#         """
#         Odoo 17: send a message into Discuss as a private chat.
#         Ensures all targets (and the author) are members of the channel.
#         Reuses a channel with the exact same membership, or creates one.
#         """
#         try:
#             # --- Resolve partners ---
#             partners = self.env['res.users'].browse(user_ids).mapped('partner_id')
#             if not partners:
#                 _logger.warning("send_chat_notification: no partners for user_ids=%s", user_ids)
#                 return

#             # Always include the author so they can see the chat
#             author_partner = self.env.user.partner_id
#             desired_partner_ids = set(partners.ids + [author_partner.id])

#             _logger.info("CHAT NOTIF: desired partners = %s", desired_partner_ids)

#             Channel = self.env['discuss.channel'].sudo()

#             # --- Find a channel whose membership EXACTLY matches desired partners ---
#             candidates = Channel.search([
#                 ('channel_type', '=', 'chat'),
#                 ('channel_member_ids.partner_id', 'in', list(desired_partner_ids)),
#             ], order='id desc')  # newest first; we’ll filter in Python

#             channel = False
#             for ch in candidates:
#                 ch_partner_ids = set(ch.channel_member_ids.mapped('partner_id').ids)
#                 if ch_partner_ids == desired_partner_ids:
#                     channel = ch
#                     break

#             # --- Create channel if not found ---
#             if not channel:
#                 members_vals = [(0, 0, {'partner_id': pid}) for pid in desired_partner_ids]
#                 channel = Channel.create({
#                     'name': 'System Notifications',
#                     'channel_type': 'chat',
#                     'channel_member_ids': members_vals,
#                 })
#                 _logger.info("CHAT NOTIF: created channel id=%s members=%s",
#                              channel.id, desired_partner_ids)
#             else:
#                 _logger.info("CHAT NOTIF: reusing channel id=%s", channel.id)

#             # --- Post the message ---
#             channel.message_post(
#                 body=f"{title}{message}",
#                 message_type='comment',
#                 subtype_xmlid='mail.mt_comment',
#                 author_id=author_partner.id,  # make the post appear from the current user
#             )
#             _logger.info("CHAT NOTIF: message posted to channel id=%s", channel.id)

#         except Exception as e:
#             _logger.exception("CHAT NOTIF: failed to send chat notification: %s", e)





from odoo import models
import logging
from pyfcm import FCMNotification

_logger = logging.getLogger(__name__)

class NotificationManager(models.AbstractModel):
    _name = 'notification.manager'
    _description = 'Push Notification Manager'

    def send_fcm_notification(self, user_ids, title, message):
        """Sends push notification via FCM to the users' mobile app."""
        # Get user FCM tokens
        users = self.env['res.users'].browse(user_ids)
        tokens = [u.fcm_token for u in users if u.fcm_token]
        if not tokens:
            _logger.warning("No FCM tokens found for user(s): %s", user_ids)
            return

        # Path to your Firebase service account json and project_id
        service_account_file = '/absolute/path/to/service-account.json'
        project_id = 'your-firebase-project-id'

        fcm = FCMNotification(
            service_account_file=service_account_file,
            project_id=project_id
        )
        # Send to each token
        for token in tokens:
            result = fcm.notify(
                fcm_token=token,
                notification_title=title,
                notification_body=message,
            )
            _logger.info(f"FCM notification result for token {token}: {result}")

    # Optional alias if other code still calls this name
    def send_push_notification(self, user_ids, title, message, notification_type='info'):
        """
        This method prepares the notification payload for Odoo's internal
        notification service and sends it over the bus.
        """
        _logger.info("--- DEBUG: send_push_notification called ---")
        _logger.info(f"--- DEBUG: Target User IDs: {user_ids} ---")

        users = self.env['res.users'].browse(user_ids)
        if not users:
            _logger.warning("--- DEBUG: No users found for the given IDs. Aborting. ---")
            return

        # Prepare Standard Odoo 'simple_notification' Payload (Sticky Toast)
        payload = {
            'type': notification_type,
            'title': title,
            'message': message,
            'sticky': False,  # Changed to False so it disappears automatically
        }

        # Use _sendone loop for maximum reliability across different user sessions
        for user in users:
            try:
                # Send to this specific partner's simple_notification channel
                self.env['bus.bus']._sendone(user.partner_id, 'simple_notification', payload)
            except Exception as e:
                _logger.error(f"--- DEBUG: Failed to send to user {user.name}: {e}")

        _logger.info(f"--- DEBUG: _sendone loop executed for {len(users)} users. ---")

        # Call FCM for mobile push (asynchronously, no user blocking)
        self.send_fcm_notification(user_ids, title, message)

        return self.send_chat_notification(user_ids, title, message)


    def send_chat_notification(self, user_ids, title, message):
        """
        Sends a chat message notification to the given user_ids.
        Attempts 1-to-1 chat first if possible, otherwise uses a group channel.
        """
        if not user_ids:
            _logger.warning("CHAT NOTIF: No users provided.")
            return

        Partner = self.env['res.partner']
        Channel = self.env['discuss.channel']
        Message = self.env['mail.message']
        User = self.env['res.users']

        desired_partners = Partner.search([('user_ids', 'in', user_ids)])
        desired_partner_ids = desired_partners.ids

        _logger.info("CHAT NOTIF: desired partners = %s", desired_partner_ids)

        members_vals = [(0, 0, {'partner_id': pid}) for pid in desired_partner_ids]
        channel = None

        # --- Try to create 1-to-1 chat first if 2 users ---
        if len(desired_partner_ids) == 2:
            try:
                channel = Channel.create({
                    'name': 'System Notifications',
                    'channel_type': 'chat',
                    'channel_member_ids': members_vals,
                })
                _logger.info("CHAT NOTIF: created 1-to-1 chat channel id=%s members=%s", channel.id, desired_partner_ids)
            except Exception as e:
                _logger.warning("CHAT NOTIF: failed to create chat channel, falling back to group channel. Error: %s", e)

        # --- Fallback to group channel if chat not created or >2 users ---
        if not channel:
            channel = Channel.create({
                'name': 'System Notifications',
                'channel_type': 'channel',
                'channel_member_ids': members_vals,
            })
            _logger.info("CHAT NOTIF: created group channel id=%s members=%s", channel.id, desired_partner_ids)

        # --- Post the message to the created/reused channel ---
        Message.create({
            'author_id': self.env.user.partner_id.id,
            'model': 'discuss.channel',
            'res_id': channel.id,
            'message_type': 'comment',
            'subtype_id': self.env.ref('mail.mt_comment').id,
            'body': f"<b>{title}</b><br/>{message}",
        })
        _logger.info("CHAT NOTIF: message posted to channel id=%s", channel.id)

