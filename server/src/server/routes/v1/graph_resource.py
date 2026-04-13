import structlog
from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from neomodel.contrib import SemiStructuredNode
from werkzeug.exceptions import abort

from ...api_models.error import COMMON_ERRORS
from ...api_models.graph import (
    GRAPH_SEARCH_POST_INPUT,
    GRAPH_SEARCH_POST_RESPONSE,
    NODE_DELETE_RESPONSE,
    NODE_GET_LIST_RESPONSE,
    NODE_GET_SINGLE_RESPONSE,
    NODE_PATCH_INPUT,
)
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

    # later - create new
    # @graph_ns.doc(
    #     summary="Create a new node",
    #     description="Creates a new node of the specified type.",
    #     responses=COMMON_ERRORS,
    #     security="Bearer Auth",
    # )
    # @graph_ns.expect(NODE_POST_INPUT)
    # @jwt_required()
    # def post(self, nodename):
    #     ip = request.remote_addr
    #     payload = request.json or {}

    #     # get class
    #     node_class = get_node_class_from_string(node_name=nodename.lower())
    #     if not node_class:
    #         abort(400, "Invalid node type")

    #     # Determine strict vs flexible validation
    #     is_flexible = issubclass(node_class, SemiStructuredNode)
    #     defined_properties = node_class.__all_properties__

    #     # 3. Validate payload before instantiation
    #     clean_payload = {}
    #     for key, value in payload.items():
    #         if key in defined_properties:
    #             clean_payload[key] = value
    #         elif is_flexible:
    #             clean_payload[key] = value
    #         else:
    #             # Reject unknown fields on strict nodes before we even touch the database
    #             abort(400, f"Invalid field '{key}' provided for node type {nodename}")

    #     # Handle UUID Generation
    #     node_uuid_var = f"{nodename.lower()}_uuid"

    #     # If the client didn't supply a UUID, generate one for them
    #     if node_uuid_var not in clean_payload:
    #         clean_payload[node_uuid_var] = str(uuid.uuid4())

    #     # 5. Instantiate and save
    #     try:
    #         # neomodel **kwargs instantiation handles the rest
    #         new_node = node_class(**clean_payload).save()
    #     except Exception as e:
    #         # Catch neomodel validation errors (e.g., missing required fields)
    #         abort(400, f"Failed to create node: {str(e)}")

    #     return {
    #         "status": "201",
    #         "message": "Created successfully",
    #         "data": new_node.to_dict()
    #     }, 201


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
    @graph_ns.marshal_with(NODE_GET_SINGLE_RESPONSE)
    @jwt_required()
    def get(self, nodename, uuid):
        """
        Gets properties of node
        """
        ip = request.remote_addr
        api_logger.info("Getting node properties", nodename=nodename, uuid=uuid, caller_ip=ip)

        node_class = get_node_class_from_string(node_name=nodename.lower())

        if not node_class:
            abort(400, "Invalid node type")

        # format name of uuid
        # tldr, bad planning, each model is NAME_uuid
        node_uuid_var = f"{nodename.lower()}_uuid"
        # this just takes it as kwargs and then unpacks it
        node = node_class.nodes.get_or_none(**{node_uuid_var: uuid})

        if not node:
            abort(400, "Invalid node UUID")

        node_data = node.to_dict()

        return APIResponse(
            status="200",
            message="Success",
            data=node_data,
        )

    @graph_ns.doc(
        summary="Update node data",
        description="Partially updates an existing node's data.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @graph_ns.expect(NODE_PATCH_INPUT)
    @jwt_required()
    def patch(self, nodename, uuid):
        ip = request.remote_addr
        payload = request.json

        api_logger.info("Updating node", nodename=nodename, uuid=uuid, caller_ip=ip, payload=payload)

        # Get class and fetch existing node
        node_class = get_node_class_from_string(node_name=nodename.lower())
        if not node_class:
            abort(400, "Invalid node type")

        #! In short, bad planning means each model has a different uuid field, but they all follow the pattern
        #! NAME_uuid.
        #! So we have to dynamically format the lookup based on the nodename.
        #! This is a bit hacky, but it works for now without a major refactor.
        node_uuid_var = f"{nodename.lower()}_uuid"

        node = node_class.nodes.get_or_none(**{node_uuid_var: uuid})
        if not node:
            abort(404, f"{nodename} with that UUID not found")

        # Determine if the node is strict or flexible
        is_flexible = issubclass(node_class, SemiStructuredNode)

        # Get the defined properties of the class (to prevent Mass Assignment)
        # neomodel stores defined fields in __all_properties__
        # This is a tuple - so we convert to a dict.
        defined_properties = dict(node_class.__all_properties__)

        # Safely iterate and update
        for key, value in payload.items():
            # Don't let the field UUID be updated.
            # kinda patchy
            if key in [node_uuid_var, "uuid"]:
                continue

            if key in defined_properties:
                # It's a known field, safe to update
                setattr(node, key, value)
            elif is_flexible:
                # It's an unknown field, but this is an Implant (SemiStructured), so allow it
                setattr(node, key, value)
            else:
                # It's an unknown field on a strict node. Reject the whole request.
                abort(400, f"Invalid field '{key}' provided for node type {nodename}")

        # Save and return
        node.save()

        return APIResponse(
            status="200",
            message="Success",
            data=node.to_dict(),
        )

    @graph_ns.doc(
        summary="Delete a node",
        description="Deletes a specific node from the graph by its UUID.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @graph_ns.marshal_with(NODE_DELETE_RESPONSE)
    @jwt_required()
    def delete(self, nodename, uuid):
        """
        Deletes the node
        """
        ip = request.remote_addr
        api_logger.info("Deleting node", nodename=nodename, uuid=uuid, caller_ip=ip)

        node_class = get_node_class_from_string(node_name=nodename.lower())

        if not node_class:
            abort(400, "Invalid node type")

        # format name of uuid
        # tldr, bad planning, each model is NAME_uuid
        node_uuid_var = f"{nodename.lower()}_uuid"
        # this just takes it as kwargs and then unpacks it
        node = node_class.nodes.get_or_none(**{node_uuid_var: uuid})

        if not node:
            abort(400, "Invalid node UUID")

        # note - delete will auto handle the detach
        node.delete()

        return APIResponse(
            status="200",
            message="Deleted",
            data=None,
        )


# busted - not sure why
# class NodeSchema(Resource):
#     """
#     Returns the database schema for a specific node type.
#     """

#     @graph_ns.doc(
#         summary="Get node schema",
#         description="Retrieves the allowed fields, data types, and requirements for a node type.",
#         responses=COMMON_ERRORS,
#         security="Bearer Auth",
#     )
#     @graph_ns.param("nodename", "The type of node")
#     @graph_ns.response(200, "Retrieved schema successfully")  # NODE_SCHEMA_RESPONSE)
#     # @jwt_required()
#     def get(self, nodename):
#         ip = request.remote_addr
#         api_logger.info("Getting schema for node type", nodename=nodename, caller_ip=ip)

#         # 1. Resolve the class
#         node_class = get_node_class_from_string(node_name=nodename.lower())
#         if not node_class:
#             abort(400, "Invalid node type")

#         # 2. Build the base response
#         schema_data = {
#             "node_type": nodename.lower(),
#             "is_flexible": issubclass(node_class, SemiStructuredNode),
#             "fields": {},
#         }

#         # 3. Inspect neomodel properties at runtime
#         for prop_name in node_class.__all_properties__:
#             # Get the actual property object (e.g., the StringProperty instance)
#             prop_obj = getattr(node_class, prop_name)

#             # Extract its rules
#             schema_data["fields"][prop_name] = {
#                 # __class__.__name__ turns <class 'neomodel.StringProperty'> into "StringProperty"
#                 "type": prop_obj.__class__.__name__,
#                 "required": getattr(prop_obj, "required", False),
#                 "unique": getattr(prop_obj, "unique_index", False),
#                 "default_exists": getattr(prop_obj, "has_default", False),
#             }

#         return APIResponse(
#             status="200",
#             message="Success",
#             data=schema_data,
#         )


graph_ns.add_resource(Graph, "/")
graph_ns.add_resource(GraphSearch, "/search")
graph_ns.add_resource(NodeParent, "/node/<string:nodename>/")
# busted for some reason, deal with later.
# graph_ns.add_resource(NodeSchema, "/node/<string:nodename>/schema")
graph_ns.add_resource(Node, "/node/<string:nodename>/<string:uuid>")
api.add_namespace(graph_ns)
