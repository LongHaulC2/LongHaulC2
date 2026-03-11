import structlog
from flask_jwt_extended import create_access_token
from flask_restx import Namespace, Resource
from werkzeug.exceptions import BadRequest, MethodNotAllowed, NotFound, abort

from ...api_models.authentication import AUTH_LOGIN_RESPONSE, AUTH_POST_INPUT, AUTH_REGISTER_RESPONSE
from ...api_models.error import COMMON_ERRORS, ERROR_MODEL
from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLUserService
from ...instance import api
from ...utils.response import APIResponse

auth_ns = Namespace("authentication", description="Authentication")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


# Error handlers
# for ref: https://werkzeug.palletsprojects.com/en/stable/exceptions/


@auth_ns.errorhandler(BadRequest)
@auth_ns.marshal_with(ERROR_MODEL)
def handle_bad_request_and_abort(e):
    """
    Catches all Werkzeug/RESTX aborts and ensures they
    match our {status, message, data} format. This will not catch
    things like "raise valueerror", hence why there are other error handlers  too
    """
    server_logger.error("An error occured", error=e, message=str(e))

    return {
        "status": str(e.code),
        "message": getattr(e, "message", str(e)),
        "data": getattr(e, "data", {}),  # if abort is called, this will include it
    }, e.code


@auth_ns.errorhandler(NotFound)
@auth_ns.marshal_with(ERROR_MODEL)
def handle_not_found(e):
    server_logger.error("An error occured", error=e)
    return {"status": "404", "message": "Not Found", "data": ""}, 404


@auth_ns.errorhandler(MethodNotAllowed)
@auth_ns.marshal_with(ERROR_MODEL)
def handle_method_not_allowed_error(e):
    server_logger.error("An error occured", error=e)
    # ! e.get_response().headers, allows the ALLOW header through, otherwise, schemathesis will fail
    return {"status": "405", "message": "Method not allowed", "data": None}, 405, e.get_response().headers


@auth_ns.errorhandler(Exception)
@auth_ns.marshal_with(ERROR_MODEL)
def handle_general_error(e):
    server_logger.error("An error occured", error=e)
    return {"status": "500", "message": "An internal error occurred", "data": None}, 500


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
            response = {"token": access_token}
            # Return immediately
            return APIResponse(status="200", message="Login Successful", data=response)

        # Return immediately
        return APIResponse(status="200", message="Login Failed", data={})


class Register(Resource):
    @auth_ns.doc(
        responses=COMMON_ERRORS,
    )
    @auth_ns.expect(AUTH_POST_INPUT, validate=False)  # flip to True to enforce
    @auth_ns.response(200, "User registered successfully", AUTH_REGISTER_RESPONSE)
    @auth_ns.marshal_with(AUTH_REGISTER_RESPONSE)
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

api.add_namespace(auth_ns)
