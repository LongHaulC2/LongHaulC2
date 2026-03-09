import structlog
from flask import request
from flask_restx import Namespace, Resource
from werkzeug.exceptions import BadRequest, MethodNotAllowed, NotFound

from ...api_models.error import COMMON_ERRORS, ERROR_MODEL
from ...api_models.listener import LISTENER_GET_RESPONSE
from ...instance import api
from ...modules.status.status import get_health_status
from ...utils.response import APIResponse

health_ns = Namespace("health", description="Health related endpoints")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


@health_ns.errorhandler(NotFound)
@health_ns.marshal_with(ERROR_MODEL)
def handle_not_found(e):
    server_logger.error("An error occured", error=e)
    return {"status": "404", "message": "Not Found", "data": ""}, 404


@health_ns.errorhandler(MethodNotAllowed)
@health_ns.marshal_with(ERROR_MODEL)
def handle_method_not_allowed_error(e):
    server_logger.error("An error occured", error=e)
    # ! e.get_response().headers, allows the ALLOW header through, otherwise, schemathesis will fail
    return {"status": "405", "message": "Method not allowed", "data": None}, 405, e.get_response().headers


@health_ns.errorhandler(BadRequest)
@health_ns.marshal_with(ERROR_MODEL)
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


@health_ns.errorhandler(Exception)
@health_ns.marshal_with(ERROR_MODEL)
def handle_general_error(e):
    server_logger.error("An error occured", error=e)
    return {"status": "500", "message": "An internal error occurred", "data": None}, 500


class Health(Resource):
    @health_ns.doc(
        summary="Get health",
        description="Retrieves all the health data",
        responses=COMMON_ERRORS,
    )
    @health_ns.response(200, "Retrieved health data successfully", LISTENER_GET_RESPONSE)
    # @health_ns.marshal_with(LISTENER_GET_RESPONSE)
    def get(self):
        """
        Gets graph data based on user supplied ID
        """
        ip = request.remote_addr

        api_logger.debug("Getting health data", caller_ip=ip)

        health_dict = get_health_status()

        api_response = APIResponse(
            status="200",
            message="Success",
            data=health_dict,
        )
        return api_response.jsonify()


health_ns.add_resource(Health, "/")

api.add_namespace(health_ns)
