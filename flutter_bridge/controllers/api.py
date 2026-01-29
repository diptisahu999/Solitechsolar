from odoo import http
from odoo.http import request
from ..utils.fcm import send_push
from firebase_admin import messaging
import json


class RegisterFCMTokenAPI(http.Controller):

    # =====================================================
    # ✅ POST REGISTER TOKEN
    # =====================================================

    @http.route(
        '/api/push/register',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False
    )
    def register_device_post(self, **kwargs):

        import json
        data = json.loads(request.httprequest.data or '{}')

        fcm_token = data.get('fcm_token')
        platform = data.get('platform')

        if not fcm_token or not platform:
            return request.make_response(
                json.dumps({
                    "status": "error",
                    "message": "fcm_token and platform are required"
                }),
                headers=[('Content-Type', 'application/json')]
            )

        Device = request.env['push.device'].sudo()

        # 🔥 update if exists, else create
        device = Device.search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if device:
            device.write({
                'fcm_token': fcm_token,
                'platform': platform
            })
            action = "updated"
        else:
            Device.create({
                'user_id': request.env.user.id,
                'fcm_token': fcm_token,
                'platform': platform
            })
            action = "created"

        return request.make_response(
            json.dumps({
                "status": "ok",
                "action": action,
                "message": f"FCM token {action} successfully"
            }),
            headers=[('Content-Type', 'application/json')]
        )
    

    # =====================================================
    # ✅ SEND USER NOTIFICATION
    # =====================================================

    @http.route(
        '/api/push/send/users',
        type='http', 
        auth='user',
        methods=['POST'],
        csrf=False
    )
    def send_push_to_users(self, **kwargs):
        data = json.loads(request.httprequest.data or '{}')

        result = request.env['push.service'].sudo().send_to_users(
            user_ids=data['user_ids'],
            title=data['title'],
            body=data['body']
        )

        return request.make_response(
            json.dumps(result), 
            headers=[('Content-Type', 'application/json')]
        )


    # if http not work then use this

    # @http.route(
    #     '/api/push/send/users',
    #     type='json',
    #     auth='user',
    #     methods=['POST'],
    #     csrf=False
    # )
    # def send_push_to_users(self, **kwargs):
    #     data = request.jsonrequest

    #     if not data.get('user_ids') or not data.get('title') or not data.get('body'):
    #         return {"status": "error", "message": "Missing required fields"}

    #     return request.env['push.service'].sudo().send_to_users(
    #         user_ids=data['user_ids'],
    #         title=data['title'],
    #         body=data['body']
    #     )
