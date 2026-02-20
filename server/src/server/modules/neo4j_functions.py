# neo4j functions
from ..db.mysql_connector import get_mysql_session
from ..db.neo4j_models import (
    Neo4jImplantNode,
    Neo4jNetworkGatewayNode,
    Neo4jNetworkNode,
)
from .mysql_functions import ImplantService, MySQLImplantTaskService
from .redis_functions import RedisImplantTaskService


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
        net = Neo4jNetworkNode(cidr=cidr_value)
        net.save()

        # check if exists, if not, create
        net = Neo4jNetworkNode.nodes.get_or_none(cidr=cidr_value)
        if not net:
            net = Neo4jNetworkNode(cidr=cidr_value)
            net.save()

        # Connect the implant to the network node
        # This creates the (Implant)-[:CONNECTED_TO]->(Network) relationship in Neo4j
        if self.implant_node:
            self.implant_node.connected_to.connect(net)

    def _check_network_gateway(self):
        """
        Function for network gateways related nodes in neo4j

        If network gateway does not already exist (note... clash with CIDR's, use gateways as well?)
        then create a network node
        """
        # somehow get network metadata, not sure entry point yet

        # pull neo4j nodes
        # if netowrk node for that cidr doesn't exist

        implant_external_ip = self.metadata.get("external_ip", "")

        if not implant_external_ip:
            return

        gw = Neo4jNetworkGatewayNode(host=implant_external_ip)
        gw.save()
