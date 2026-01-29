import firebase_admin
from firebase_admin import credentials, messaging
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

cred = credentials.Certificate(
    os.path.join(BASE_DIR, '/www/wwwroot/python/firebase_key.json')
)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)


def send_push(token, title, body, data=None):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        token=token,
    )
    return messaging.send(message)
