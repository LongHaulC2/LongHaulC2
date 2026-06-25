import structlog
from flask_jwt_extended.exceptions import JWTExtendedException, NoAuthorizationError
from jwt.exceptions import ExpiredSignatureError, InvalidSignatureError, PyJWTError
from werkzeug.exceptions import BadRequest, MethodNotAllowed, NotFound

from ..api_models.error import ERROR_MODEL
from ..instance import api

server_logger = structlog.get_logger("server")


# Catch missing headers or completely malformed requests
@api.errorhandler(NoAuthorizationError)
def handle_auth_error(e):  # noqa - e is needed
    server_logger.warning("Unauthorized access attempt: Missing Authorization Header")
    return {"status": "401", "message": "Unauthorized: Missing or invalid Authorization header", "data": None}, 401


# Catch expired tokens
@api.errorhandler(ExpiredSignatureError)
def handle_expired_error(e):  # noqa - e is needed
    server_logger.warning("Unauthorized access attempt: Token expired")
    return {"status": "401", "message": "Unauthorized: The token has expired", "data": None}, 401


# Catch invalid signatures (like the one you got earlier)
@api.errorhandler(InvalidSignatureError)
def handle_invalid_signature_error(e):  # noqa - e is needed
    server_logger.warning("Unauthorized access attempt: Invalid signature")
    return {"status": "401", "message": "Unauthorized: Invalid token signature", "data": None}, 401


# Global fallback for any other JWT or PyJWT issues
@api.errorhandler(JWTExtendedException)
@api.errorhandler(PyJWTError)
def handle_jwt_general_error(e):
    server_logger.warning("JWT Error", error=str(e))
    return {"status": "401", "message": f"Unauthorized: {str(e)}", "data": None}, 401


# not found
@api.errorhandler(NotFound)
@api.marshal_with(ERROR_MODEL)
def handle_not_found(e):
    server_logger.error("An error occurred", error=e)
    return {"status": "404", "message": "Not Found", "data": ""}, 404


# meth not allowed
@api.errorhandler(MethodNotAllowed)
@api.marshal_with(ERROR_MODEL)
def handle_method_not_allowed_error(e):
    server_logger.error("An error occurred", error=e)
    # ! e.get_response().headers, allows the ALLOW header through, otherwise, schemathesis will fail
    return {"status": "405", "message": "Method not allowed", "data": None}, 405, e.get_response().headers


# bad req
@api.errorhandler(BadRequest)
@api.marshal_with(ERROR_MODEL)
def handle_bad_request_and_abort(e):
    """
    Catches all Werkzeug/RESTX aborts and ensures they
    match our {status, message, data} format. This will not catch
    things like "raise valueerror", hence why there are other error handlers  too
    """
    server_logger.error("An error occurred", error=e, message=str(e))

    return {
        "status": str(e.code),
        "message": getattr(e, "message", str(e)),
        "data": getattr(e, "data", {}),  # if abort is called, this will include it
    }, e.code


# anything else
@api.errorhandler(Exception)
@api.marshal_with(ERROR_MODEL)
def handle_general_error(e):
    # This acts as the ultimate global catch-all for any unhandled crashes
    server_logger.error("An internal error occurred", error=e)
    return {"status": "500", "message": "An internal error occurred", "data": None}, 500
