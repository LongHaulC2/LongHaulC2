import structlog
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from werkzeug.exceptions import abort

from ...api_models.authentication import AUTH_LOGIN_RESPONSE, AUTH_POST_INPUT, AUTH_REGISTER_RESPONSE
from ...api_models.error import COMMON_ERRORS
from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLUserService
from ...instance import api
from ...utils.response import APIResponse

auth_ns = Namespace("authentication", description="Authentication")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


class Auth(Resource):
    @auth_ns.doc(
        responses=COMMON_ERRORS,
    )
    @auth_ns.expect(AUTH_POST_INPUT, validate=False)  # flip to True to enforce
    @auth_ns.response(200, "Build initiated", AUTH_LOGIN_RESPONSE)
    @auth_ns.marshal_with(AUTH_LOGIN_RESPONSE)
    def post(self):
        """
        Login, returns a JWT if successful
        """

        data = auth_ns.payload

        # note - with flaskrestx, if/when these autothrow, they'll throw a
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            abort(400, "Missing username or password in payload")

        with get_mysql_session() as session:
            user_login = MySQLUserService(session)
            user_login.validate_password(username=username, password=password)

        if user_login:
            access_token = create_access_token(identity=username)
            refresh_token = create_refresh_token(identity=username)

            response = {"access_token": access_token, "refresh_token": refresh_token}
            # Return immediately
            return APIResponse(status="200", message="Login Successful", data=response)

        # Return immediately
        return APIResponse(status="200", message="Login Failed", data={})


class Refresh(Resource):
    @auth_ns.doc(security="Bearer Auth")
    @jwt_required(refresh=True)  # only takes refresh tokens
    def post(self):
        """Exchange a valid refresh token for a new access token"""
        current_user = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user)

        return APIResponse(
            status="200", message="Token refreshed successfully", data={"access_token": new_access_token}
        )


class Register(Resource):
    @auth_ns.doc(
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @auth_ns.expect(AUTH_POST_INPUT, validate=False)  # flip to True to enforce
    @auth_ns.response(200, "User registered successfully", AUTH_REGISTER_RESPONSE)
    @auth_ns.marshal_with(AUTH_REGISTER_RESPONSE)
    @jwt_required()
    def post(self):
        """
        Register a new user.
        """

        data = auth_ns.payload

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            abort(400, "Missing username or password in payload")

        with get_mysql_session() as session:
            user_login = MySQLUserService(session)
            user_login.register_user(username=username, password=password)

        return APIResponse(status="200", message="User registered successfully")


auth_ns.add_resource(Auth, "/")
auth_ns.add_resource(Register, "/register")
auth_ns.add_resource(Refresh, "/refresh")

api.add_namespace(auth_ns)
