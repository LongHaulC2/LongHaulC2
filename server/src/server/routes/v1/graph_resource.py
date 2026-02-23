import structlog
from flask import request
from flask_restx import Namespace, Resource
from neomodel import db

from ...api_models.error import COMMON_ERRORS
from ...api_models.listener import LISTENER_GET_RESPONSE
from ...instance import api
from ...utils.response import APIResponse

graph_ns = Namespace("graph", description="Graph related endpoints")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


# Error handlers
@graph_ns.errorhandler(ValueError)
def handle_value_error(e):
    return {"status": "400", "message": str(e), "data": None}, 400


@graph_ns.errorhandler(Exception)
def handle_general_error(e):
    return {"status": "500", "message": "An internal error occurred", "data": None}, 500


class Graph(Resource):
    @graph_ns.doc(
        summary="Get graph",
        description="Retrieves all the graph data, seperated into ...,..., ...",
        responses=COMMON_ERRORS,
    )
    @graph_ns.response(200, "Retrieved graph data successfully", LISTENER_GET_RESPONSE)
    # @graph_ns.marshal_with(LISTENER_GET_RESPONSE)
    def get(self):
        """
        Gets graph data based on user supplied ID
        """
        ip = request.remote_addr

        api_logger.info("Getting graph data", caller_ip=ip)

        query = """
            // 1. Fetch Categories
            CALL {
                MATCH (n)
                WITH DISTINCT labels(n)[0] AS label
                RETURN collect({name: label}) AS categories
            }

            // 2. Fetch Nodes
            CALL {
                MATCH (n)
                RETURN collect({
                    id: toString(elementId(n)),
                    name: CASE
                        WHEN "Neo4jImplantNode" IN labels(n) THEN coalesce(n.implant_uuid, "Unknown")
                        WHEN "Neo4jNetworkNode" IN labels(n) THEN coalesce(n.cidr, "Unknown")
                        WHEN "Neo4jNetworkGatewayNode" IN labels(n) THEN coalesce(n.host, "Unknown")
                        WHEN "Neo4jHostNode" IN labels(n) THEN coalesce(n.address, "Unknown")
                        ELSE coalesce(n.ip_address, n.hostname, n.process, "Unknown_" + toString(elementId(n)))
                    END,
                    category: labels(n)[0],
                    props: properties(n)
                }) AS nodes
            }

            // 3. Fetch Links
            CALL {
                MATCH (a)-[r]->(b)
                RETURN collect({
                    source: toString(elementId(a)),
                    target: toString(elementId(b)),
                    value: type(r),
                    props: properties(r)
                }) AS links
            }

            // 4. Return as a single structured dictionary
            RETURN {
                categories: categories,
                nodes: nodes,
                links: links
            } AS graph_data;
        """

        # Run the query
        results, _ = db.cypher_query(query)

        # results[0][0] contains our beautifully formatted dictionary straight from Neo4j
        graph_dict = results[0][0] if results and results[0] else {"categories": [], "nodes": [], "links": []}

        api_response = APIResponse(
            status="200",
            message="Success",
            data=graph_dict,
        )
        return api_response.jsonify()


graph_ns.add_resource(Graph, "/")

api.add_namespace(graph_ns)
