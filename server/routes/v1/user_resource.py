import base64
import io

import pyotp
import qrcode
import structlog
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields
from werkzeug.exceptions import abort

from ...db.audit import log_audit
from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLUserService
from ...instance import api
from ...utils.response import APIResponse

user_ns = Namespace("users", description="User Management")
server_logger = structlog.getLogger("server")

USER_MODEL = api.model(
    "USER_MODEL",
    {
        "username": fields.String(description="Username"),
        "has_totp": fields.Boolean(description="Whether TOTP 2FA is enabled"),
    },
)

CHANGE_PASSWORD_INPUT = api.model(
    "CHANGE_PASSWORD_INPUT",
    {
        "old_password": fields.String(required=True),
        "new_password": fields.String(required=True),
    },
)

TOTP_SETUP_RESPONSE = api.model(
    "TOTP_SETUP_RESPONSE",
    {
        "secret": fields.String(description="TOTP secret for authenticator app"),
        "provisioning_uri": fields.String(description="otpauth:// URI for QR code"),
    },
)

TOTP_VERIFY_INPUT = api.model(
    "TOTP_VERIFY_INPUT",
    {
        "code": fields.String(required=True, description="6-digit TOTP code"),
    },
)


class UserList(Resource):
    @jwt_required()
    def get(self):
        """List all registered users"""
        with get_mysql_session() as session:
            svc = MySQLUserService(session)
            users = svc.list_users()
        return APIResponse(status="200", message="Success", data=users)


class UserSelf(Resource):
    @jwt_required()
    def get(self):
        """Get current user's profile info"""
        username = get_jwt_identity()
        with get_mysql_session() as session:
            svc = MySQLUserService(session)
            user = svc.get_user(username)
        if not user:
            abort(404, "User not found")
        return APIResponse(status="200", message="Success", data=user)

    @jwt_required()
    def delete(self):
        """Delete your own account"""
        username = get_jwt_identity()
        with get_mysql_session() as session:
            svc = MySQLUserService(session)
            deleted = svc.delete_user(username)
        if not deleted:
            abort(404, "User not found")
        return APIResponse(status="200", message="Account deleted")


class UserDelete(Resource):
    @jwt_required()
    def delete(self, username):
        """Delete a user by username (admin action)"""
        with get_mysql_session() as session:
            svc = MySQLUserService(session)
            deleted = svc.delete_user(username)
        if not deleted:
            abort(404, "User not found")
        log_audit(get_jwt_identity(), "user_deleted", "user", username)
        return APIResponse(status="200", message=f"User '{username}' deleted")


class ChangePassword(Resource):
    @jwt_required()
    @user_ns.expect(CHANGE_PASSWORD_INPUT, validate=False)
    def put(self):
        """Change the current user's password"""
        username = get_jwt_identity()
        data = user_ns.payload

        old_password = data.get("old_password")
        new_password = data.get("new_password")
        if not old_password or not new_password:
            abort(400, "Missing old_password or new_password")

        with get_mysql_session() as session:
            svc = MySQLUserService(session)
            changed = svc.change_password(username, old_password, new_password)

        if not changed:
            abort(401, "Current password is incorrect")
        return APIResponse(status="200", message="Password changed successfully")


class TOTPSetup(Resource):
    @jwt_required()
    def post(self):
        """Generate a new TOTP secret and return it for authenticator setup"""
        username = get_jwt_identity()
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=username, issuer_name="LongHaulC2")

        with get_mysql_session() as session:
            svc = MySQLUserService(session)
            svc.set_totp_secret(username, secret)

        img = qrcode.make(provisioning_uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return APIResponse(
            status="200",
            message="TOTP secret generated. Verify with a code to confirm.",
            data={
                "secret": secret,
                "provisioning_uri": provisioning_uri,
                "qr_code": f"data:image/png;base64,{qr_b64}",
            },
        )

    @jwt_required()
    def delete(self):
        """Disable TOTP 2FA"""
        username = get_jwt_identity()
        with get_mysql_session() as session:
            svc = MySQLUserService(session)
            svc.set_totp_secret(username, None)
        return APIResponse(status="200", message="TOTP disabled")


class TOTPVerify(Resource):
    @jwt_required()
    @user_ns.expect(TOTP_VERIFY_INPUT, validate=False)
    def post(self):
        """Verify a TOTP code against the stored secret"""
        username = get_jwt_identity()
        data = user_ns.payload
        code = data.get("code")
        if not code:
            abort(400, "Missing TOTP code")

        with get_mysql_session() as session:
            svc = MySQLUserService(session)
            secret = svc.get_totp_secret(username)

        if not secret:
            abort(400, "TOTP not configured for this user")

        totp = pyotp.TOTP(secret)
        if not totp.verify(code):
            abort(401, "Invalid TOTP code")
        return APIResponse(status="200", message="TOTP code verified")


user_ns.add_resource(UserList, "/")
user_ns.add_resource(UserSelf, "/me")
user_ns.add_resource(UserDelete, "/<string:username>")
user_ns.add_resource(ChangePassword, "/password")
user_ns.add_resource(TOTPSetup, "/totp")
user_ns.add_resource(TOTPVerify, "/totp/verify")

api.add_namespace(user_ns)
