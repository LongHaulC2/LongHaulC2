import structlog
from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from ...api_models.error import COMMON_ERRORS
from ...api_models.graph import GRAPH_SEARCH_POST_INPUT, GRAPH_SEARCH_POST_RESPONSE
from ...api_models.listener import LISTENER_GET_RESPONSE
from ...db.neo4j_functions import Neo4jCoreService
from ...instance import api
from ...utils.response import APIResponse

graph_ns = Namespace("graph", description="Graph related endpoints")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


class Graph(Resource):
    @graph_ns.doc(
        summary="Get graph",
        description="Retrieves all the graph data, seperated into ...,..., ...",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @graph_ns.response(200, "Retrieved graph data successfully", LISTENER_GET_RESPONSE)
    # @graph_ns.marshal_with(LISTENER_GET_RESPONSE)
    @jwt_required()
    def get(self):
        """
        Gets graph data based on user supplied ID
        """
        ip = request.remote_addr

        api_logger.info("Getting graph data", caller_ip=ip)

        graph_dict = Neo4jCoreService.search_graph_structured(search_term="*")

        api_response = APIResponse(
            status="200",
            message="Success",
            data=graph_dict,
        )
        return api_response.jsonify()


class GraphSearch(Resource):
    @graph_ns.doc(
        summary="Search for an implant",
        description="Search for an implant with fields that match the supplied term.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @graph_ns.expect(GRAPH_SEARCH_POST_INPUT)
    @graph_ns.response(200, "A list of all found nodes", GRAPH_SEARCH_POST_RESPONSE)
    @graph_ns.marshal_with(GRAPH_SEARCH_POST_RESPONSE)
    # @jwt_required()
    def post(self):
        """
        Search for an implant
        """
        ip = request.remote_addr
        search_term = request.json.get("search_term")
        api_logger.info("Searching graph", search_term=search_term, caller_ip=ip)

        graph_dict = Neo4jCoreService.search_graph_structured(search_term=search_term)

        return APIResponse(status="200", message="Success", data=graph_dict)


graph_ns.add_resource(Graph, "/")
graph_ns.add_resource(GraphSearch, "/search")

api.add_namespace(graph_ns)
