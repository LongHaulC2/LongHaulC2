import structlog
from flask import request
from flask_restx import Namespace, Resource

from ...api_models.error import COMMON_ERRORS
from ...api_models.listener import LISTENER_GET_RESPONSE
from ...instance import api
from ...modules.status.status import get_health_status
from ...utils.response import APIResponse

health_ns = Namespace("health", description="Health related endpoints")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


# Error handlers
@health_ns.errorhandler(ValueError)
def handle_value_error(e):
    return {"status": "400", "message": str(e), "data": None}, 400


@health_ns.errorhandler(Exception)
def handle_general_error(e):
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

        api_logger.info("Getting health data", caller_ip=ip)

        health_dict = get_health_status()

        api_response = APIResponse(
            status="200",
            message="Success",
            data=health_dict,
        )
        return api_response.jsonify()


health_ns.add_resource(Health, "/")

api.add_namespace(health_ns)
