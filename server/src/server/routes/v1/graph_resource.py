import logging
from dataclasses import asdict

from edwh_uuid7 import uuid7
from flask import request
from flask_restx import Namespace, Resource, fields

from ...api_models.error import *
from ...api_models.listener import *
from ...db.mysql_connector import get_mysql_session
from ...instance import api
from ...listeners.supervisor import start_listener, stop_listener
from ...modules.mysql_functions import ListenerService
from ...schemas.listeners import ListenerCreate
from ...utils.checks import check_type
from ...utils.response import APIResponse

graph_ns = Namespace("graph", description="Graph related endpoints")
api_logger = logging.getLogger("api")
server_logger = logging.getLogger("server")


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

        api_logger.info(
            f"Getting graph data",
            extra={
                "caller_ip": ip,
            },
        )

        # hacky, quick implementation to get this data here
        from neomodel import db
        from neomodel.integration.pandas import DataFrame, to_dataframe

        # this looks like a lot, all it is is grabbing the data, and cleaning it a bit (i.e. non str -> str), then converting to a list of dicts
        # Get nodes - note, case
        nodes_query = """
                MATCH (n) 
                RETURN DISTINCT elementId(n) AS id, 
                    //decides what name is. 
                    CASE 
                        WHEN "Neo4jImplantNode" IN labels(n) THEN n.system_hostname
                        WHEN "Neo4jNetworkNode" IN labels(n) THEN n.cidr
                        WHEN "Neo4jNetworkGatewayNode" IN labels(n) THEN n.host
                        ELSE "Unknown Node"
                    //this actually sets the name here:
                    END AS name,
                    // and the label to coordinate
                    CASE 
                        WHEN "Neo4jImplantNode" IN labels(n) THEN 0 
                        WHEN "Neo4jNetworkNode" IN labels(n) THEN 1
                        WHEN "Neo4jNetworkGatewayNode" IN labels(n) THEN 2
                        ELSE 0 
                    END AS category, 
                    properties(n) AS props;
                """

        # Pass the query directly into the wrapper
        df_nodes = to_dataframe(db.cypher_query(nodes_query, resolve_objects=True))

        # Apply ECharts formatting
        df_nodes["id"] = df_nodes["id"].astype(str)
        df_nodes["name"] = df_nodes["name"].fillna("Unknown_" + df_nodes["id"])
        clean_nodes = df_nodes.to_dict("records")

        # Get links
        links_query = """MATCH (a)-[r]->(b) RETURN elementId(a) AS source, elementId(b) AS target, type(r) AS value, properties(r) AS props;"""

        df_links = to_dataframe(db.cypher_query(links_query, resolve_objects=True))

        df_links["source"] = df_links["source"].astype(str)
        df_links["target"] = df_links["target"].astype(str)
        clean_links = df_links.to_dict("records")

        # get categories
        categories_query = (
            """MATCH (n) UNWIND labels(n) AS label RETURN DISTINCT label;"""
        )

        df_cats = to_dataframe(db.cypher_query(categories_query, resolve_objects=True))

        df_cats = df_cats.rename(columns={"label": "name"})
        clean_categories = df_cats.to_dict("records")

        # Get categories
        categories_query = (
            """MATCH (n) UNWIND labels(n) AS label RETURN DISTINCT label;"""
        )
        c_results, c_cols = db.cypher_query(categories_query, resolve_objects=True)

        df_cats = DataFrame(c_results, columns=c_cols)
        # ECharts expects the category key to be "name", not "label"
        df_cats = df_cats.rename(columns={"label": "name"})
        clean_categories = df_cats.to_dict("records")

        graph_dict = {
            "nodes": clean_nodes,
            "links": clean_links,
            "categories": clean_categories,
        }

        api_response = APIResponse(
            status="200",
            message="Success",
            data=graph_dict,
        )
        return api_response.jsonify()


graph_ns.add_resource(Graph, "/")

api.add_namespace(graph_ns)
