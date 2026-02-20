# neo4j functions
import logging

from ..db.mysql_connector import get_mysql_session
from ..db.neo4j_models import (
    Neo4jImplantNode,
    Neo4jNetworkGatewayNode,
    Neo4jNetworkNode,
)
from .mysql_functions import ImplantService, MySQLImplantTaskService
from .redis_functions import RedisImplantTaskService

server_logger = logging.getLogger("server")


"""
Okoay general architectural rules:
 - Check if node exists before hand. If not, safe to create. If so, lookup node/acces obejct 
 and do what you need with it. This should be what safe/not cause weird duplicate problems
"""


class Neo4jImplantNodeService:
    def __init__(self, implant_uuid):
        self.implant_uuid = implant_uuid

        self.metadata: dict

    def init_node(self, **kwargs):
        """
        implant_uuid: prim key for implant_uuid
        kwargs: all things for metadata

        A function for initing (and maybe updating) a node in neo4j

        makes it easier to just call thsi than call neo4j stuff a ton.

        adds in correlation to the node too


        """

        # get metadata from db (mysql is still source of truth for metadata)
        # implant_metadata = {}
        # with get_mysql_session() as session:
        #     implant_metadata = ImplantService(session)

        # unpack dict into neo4j implant to get all metadata
        self.implant_node = Neo4jImplantNode(implant_uuid=self.implant_uuid, **kwargs)
        self.implant_node.save()

        # set self metadata to current metadata, it has the chance of being stale
        self.metadata = kwargs

        # call update neo4j
        self.populate_neo4j_with_implant_metadata()

    def populate_neo4j_with_implant_metadata(self):
        self._check_network()
        self._check_network_gateway()
        self._check_network_to_gateway()

    def _check_network(self):
        """
        Function for network related nodes in neo4j

        If network does not already exist (note... clash with CIDR's, use gateways as well?)
        then create a network node
        """
        # somehow get network metadata, not sure entry point yet

        # pull neo4j nodes
        # if netowrk node for that cidr doesn't exist

        # placeholder holdover for network until we get internal ip metadata
        cidr_value = self.metadata.get("cidr", "10.0.0.0/24")

        # check if exists, if not, create
        net_node = Neo4jNetworkNode.nodes.get_or_none(cidr=cidr_value)
        if not net_node:
            net_node = Neo4jNetworkNode(cidr=cidr_value)
            net_node.save()

        # Connect the implant to the network node
        # This creates the (Implant)-[:CONNECTED_TO]->(Network) relationship in Neo4j
        if self.implant_node:
            self.implant_node.connected_to.connect(net_node)

    def _check_network_gateway(self):
        """
        Function for network gateway. This assumes that the gateway is the gateway of the network the implant is on, as provided in the metadata

        If network gateway does not already exist (note... clash with CIDR's, use gateways as well?)
        then create a network node
        """
        # somehow get network metadata, not sure entry point yet

        # pull neo4j nodes
        # if netowrk node for that cidr doesn't exist

        # change to gateway when we get it, for now, use ext ip?
        implant_network_gateway = self.metadata.get("network_gateway", "1.1.1.1")

        if not implant_network_gateway:
            server_logger.warning("No network_gateway found for implant")
            return

        gw_node = Neo4jNetworkGatewayNode.nodes.get_or_none(
            host=implant_network_gateway
        )
        if not gw_node:
            gw_node = Neo4jNetworkGatewayNode(host=implant_network_gateway)
            gw_node.save()

    def _check_network_to_gateway(self):
        """
        Links the implant's local network segment to its external gateway.
        Requires both 'cidr' and 'external_ip' to exist in the metadata.
        """
        # Pull from metadata
        # placeholders for now
        cidr_value = self.metadata.get("cidr", "10.0.0.0/24")
        implant_network_gateway = self.metadata.get("network_gateway", "1.1.1.1")

        # If we are missing either the cidr or ext ip we can't draw the link
        if not cidr_value or not implant_network_gateway:
            server_logger.warning(
                "Missing CIDR or implant_network_gateway; skipping network-to-gateway link."
            )
            return

        # Safely get or create BOTH nodes
        net_node = Neo4jNetworkNode.get_or_create({"cidr": cidr_value})[0]
        gw_node = Neo4jNetworkGatewayNode.get_or_create(
            {"host": implant_network_gateway}
        )[0]

        # Connect them using the 'has_gateway' relationship defined on Neo4jNetworkNode
        # Check if they are already connected first to avoid duplicate relationship edges
        if not net_node.has_gateway.is_connected(gw_node):
            net_node.has_gateway.connect(gw_node)
            server_logger.info(
                f"Linked Network ({cidr_value}) -> Gateway ({implant_network_gateway})"
            )
