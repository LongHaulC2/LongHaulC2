import structlog
from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from werkzeug.exceptions import abort

from ...api_models.error import COMMON_ERRORS
from ...api_models.graph import GRAPH_SEARCH_POST_INPUT, GRAPH_SEARCH_POST_RESPONSE, NODE_GET_LIST_RESPONSE
from ...api_models.listener import LISTENER_GET_RESPONSE
from ...db.neo4j_functions import Neo4jCoreService
from ...db.neo4j_models import get_node_class_from_string
from ...instance import api
from ...utils.response import APIResponse

graph_ns = Namespace("graph", description="Graph related endpoints")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


class Graph(Resource):
    @graph_ns.doc(
        summary="Get graph",
        description="Retrieves all the graph data.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @graph_ns.response(200, "Retrieved graph data successfully", LISTENER_GET_RESPONSE)
    # @graph_ns.marshal_with(LISTENER_GET_RESPONSE)
    @jwt_required()
    def get(self):
        """
        Gets all the graph data: Nodes, relationships
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


class NodeParent(Resource):
    """
    Manages parent nodes, as a whole

    GET /graph/node/<nodename>/`: Lists instances of this node type (e.g., returns a list of all current beacons/agents)
    `POST /graph/node/<nodename>/`: Create new node. UUID returned

    """

    @graph_ns.doc(
        summary="List nodes by type",
        description="Lists all instances of a specific node type.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @graph_ns.marshal_with(NODE_GET_LIST_RESPONSE)
    @jwt_required()
    def get(self, nodename):
        """
        Lists instances of this node type
        """
        ip = request.remote_addr
        api_logger.info("Listing nodes by type", nodename=nodename, caller_ip=ip)

        # lowering the passed in nodename string, to match the class lookup
        node_class = get_node_class_from_string(node_name=nodename.lower())

        if not node_class:
            abort(400, "Invalid node type")

        # get all nodes:
        nodes = node_class.nodes.all()
        # then flip into a dict
        node_list = [node.to_dict() for node in nodes]

        return APIResponse(
            status="200",
            message="Success",
            data=node_list,
        )

    @graph_ns.doc(
        summary="Create a new node",
        description="Creates a new node of the specified type and returns its UUID.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @jwt_required()
    def post(self, nodename):
        """
        Create new node
        """
        ip = request.remote_addr
        payload = request.json  # noqa
        api_logger.info("Creating new node", nodename=nodename, caller_ip=ip)

        # Implementation here
        new_node_data = {}

        api_response = APIResponse(
            status="201",
            message="Created",
            data=new_node_data,
        )
        return api_response.jsonify()


class Node(Resource):
    """
    Manages individual nodes, by UUID

    `GET /graph/node/<nodename>/<uuid>`: gets properties of node
    `PATCH /graph/node/<nodename>/<uuid>`: Updates node data
    `DELETE /graph/node/<nodename>/<uuid>`: Deletes the node

    """

    @graph_ns.doc(
        summary="Get node properties",
        description="Retrieves the properties of a specific node by its UUID.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @jwt_required()
    def get(self, nodename, uuid):
        """
        Gets properties of node
        """
        ip = request.remote_addr
        api_logger.info("Getting node properties", nodename=nodename, uuid=uuid, caller_ip=ip)

        # Implementation here
        node_data = {}

        api_response = APIResponse(
            status="200",
            message="Success",
            data=node_data,
        )
        return api_response.jsonify()

    @graph_ns.doc(
        summary="Update node data",
        description="Partially updates an existing node's data based on its UUID.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @jwt_required()
    def patch(self, nodename, uuid):
        """
        Updates node data
        """
        ip = request.remote_addr
        payload = request.json  # noqa
        api_logger.info("Updating node", nodename=nodename, uuid=uuid, caller_ip=ip)

        # Implementation here
        updated_node_data = {}

        api_response = APIResponse(
            status="200",
            message="Success",
            data=updated_node_data,
        )
        return api_response.jsonify()

    @graph_ns.doc(
        summary="Delete a node",
        description="Deletes a specific node from the graph by its UUID.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @jwt_required()
    def delete(self, nodename, uuid):
        """
        Deletes the node
        """
        ip = request.remote_addr
        api_logger.info("Deleting node", nodename=nodename, uuid=uuid, caller_ip=ip)

        # Implementation here

        api_response = APIResponse(
            status="200",
            message="Deleted",
            data=None,
        )
        return api_response.jsonify()


graph_ns.add_resource(Graph, "/")
graph_ns.add_resource(GraphSearch, "/search")
graph_ns.add_resource(NodeParent, "/node/<string:nodename>/")
graph_ns.add_resource(Node, "/node/<string:nodename>/<string:uuid>")

api.add_namespace(graph_ns)
