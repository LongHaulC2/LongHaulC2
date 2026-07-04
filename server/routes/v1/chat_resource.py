import structlog
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields
from werkzeug.exceptions import abort

from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLChatService
from ...instance import api
from ...utils.response import APIResponse

chat_ns = Namespace("chat", description="Operator Chat")
server_logger = structlog.getLogger("server")

CHAT_SEND_INPUT = api.model(
    "CHAT_SEND_INPUT",
    {
        "message": fields.String(required=True, description="Chat message text"),
    },
)


class ChatMessages(Resource):
    @jwt_required()
    def get(self):
        """Get chat messages, optionally since a given message ID"""
        since_id = request.args.get("since_id", 0, type=int)

        with get_mysql_session() as session:
            svc = MySQLChatService(session)
            messages = svc.get_messages(since_id=since_id)

        return APIResponse(status="200", message="Success", data=messages)

    @jwt_required()
    @chat_ns.expect(CHAT_SEND_INPUT, validate=False)
    def post(self):
        """Send a chat message"""
        username = get_jwt_identity()
        data = chat_ns.payload
        message = data.get("message")
        if not message or not message.strip():
            abort(400, "Message cannot be empty")

        with get_mysql_session() as session:
            svc = MySQLChatService(session)
            entry = svc.send_message(sender=username, message=message.strip())

        return APIResponse(status="200", message="Message sent", data=entry)


chat_ns.add_resource(ChatMessages, "/")

api.add_namespace(chat_ns)
