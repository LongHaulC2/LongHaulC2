import structlog
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource

from ...api_models.error import COMMON_ERRORS
from ...api_models.listener import LISTENER_GET_RESPONSE
from ...instance import api
from ...modules.status.status import get_health_status
from ...utils.response import APIResponse

health_ns = Namespace("health", description="Health related endpoints")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


class Health(Resource):
    @health_ns.doc(
        summary="Get health",
        description="Retrieves all the health data",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @health_ns.response(200, "Retrieved health data successfully", LISTENER_GET_RESPONSE)
    # @health_ns.marshal_with(LISTENER_GET_RESPONSE)
    @jwt_required()
    def get(self):
        """
        Gets graph data based on user supplied ID
        """
        ip = request.remote_addr

        api_logger.debug("Getting health data", caller_ip=ip, user=get_jwt_identity())

        health_dict = get_health_status()

        api_response = APIResponse(
            status="200",
            message="Success",
            data=health_dict,
        )
        return api_response.jsonify()


health_ns.add_resource(Health, "/")

api.add_namespace(health_ns)
