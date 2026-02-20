# neo4j functions
import logging

import structlog

from ..db.mysql_connector import get_mysql_session
from ..db.neo4j_models import (
    Neo4jHostNode,
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

 Going forward, a lot of these items might be better to do on the response, i.e., create a command for it
 and then based on response, fill in data, and don't use/abuse metadata. (in the batchloop)

 Also, a field to manually update/enter values in the graph gui is a good idea, i.e., 
 click on node, have an update button/menu, and enter what property you want to add to it, etc and
 it just does the mapping for you (via init_node? it has the checks for dups, 
 so new data should be safe to add while it preseves the old)
   (i.e., joins you to a network, etc etc)
 
 """


class Neo4jImplantNodeService:
    def __init__(self, implant_uuid):
        self.implant_uuid = implant_uuid

        self.metadata: dict
        self.implant_node = None

    # def init_node(self, **kwargs):
    #     """
    #     implant_uuid: prim key for implant_uuid
    #     kwargs: all things for metadata

    #     A function for initing (and maybe updating) a node in neo4j

    #     makes it easier to just call thsi than call neo4j stuff a ton.

    #     adds in correlation to the node too

    #     """

    #     # get metadata from db (mysql is still source of truth for metadata)
    #     # implant_metadata = {}
    #     # with get_mysql_session() as session:
    #     #     implant_metadata = ImplantService(session)

    #     # unpack dict into neo4j implant to get all metadata
    #     self.implant_node = Neo4jImplantNode(implant_uuid=self.implant_uuid, **kwargs)
    #     self.implant_node.save()

    #     # set self metadata to current metadata, it has the chance of being stale
    #     self.metadata = kwargs

    #     # call update neo4j
    #     self.populate_neo4j_with_implant_metadata()

    # def init_node(self, **kwargs):
    #     self.metadata = kwargs

    #     # check if host exists first
    #     # We extract identifying info from the check-in metadata
    #     host_ip = self.metadata.get("internal_ip")  # or self.metadata.get("address")
    #     # host_mac = self.metadata.get("mac_address")

    #     # if we can find a host IP in the metadata...
    #     if host_ip:
    #         # Call the Host service to create the host, it handles "already exists" logic
    #         host_service = Neo4jHostNodeService(host_ip)
    #         host_node = host_service.register_host()
    #         # mac options later, for now, core lgoic
    #         # host_node = host_service.register_host(mac=host_mac) # no mac atm
    #     else:
    #         server_logger.warning(
    #             "Initializing implant without host metadata - identity may be orphaned"
    #         )
    #         host_node = None

    #     # create the implant node now
    #     # Using get_or_create to prevent duplicate sessions on the same UUID
    #     self.implant_node = Neo4jImplantNode.get_or_create(
    #         {"implant_uuid": self.implant_uuid}, **kwargs
    #     )[0]

    #     if host_node:
    #         # Now that 'host' is defined in the model, this will work
    #         if not self.implant_node.host.is_connected(host_node):
    #             self.implant_node.host.connect(host_node)
    #             server_logger.info("Implant linked to host")
    #         else:
    #             server_logger.debug("Implant already linked to host")

    #     # MAP THE NETWORK INFRASTRUCTURE
    #     self.populate_neo4j_with_implant_metadata()

    #     return self.implant_node

    def init_node(self, **kwargs):
        self.metadata = kwargs
        self.metadata = kwargs
        self.host_node = None

        host_ip = self.metadata.get("internal_ip")

        if host_ip:
            host_service = Neo4jHostNodeService(host_ip)
            self.host_node = host_service.register_host()  # Save to self.host_node
        else:
            server_logger.warning("Initializing implant without host metadata")

        # Then, Create or Update the implant node
        # We use find_existing to be deterministic based ONLY on the UUID
        self.implant_node = Neo4jImplantNode.find_existing(self.implant_uuid)

        if not self.implant_node:
            # Create fresh if it's the first time we've seen this UUID
            server_logger.info("Creating new Neo4jImplantNode")
            self.implant_node = Neo4jImplantNode(
                implant_uuid=self.implant_uuid, **kwargs
            ).save()
        # if it already exists, just update it
        else:
            # Update existing node with latest metadata from kwargs
            server_logger.debug("Updating existing Neo4jImplantNode")
            for key, value in kwargs.items():
                setattr(self.implant_node, key, value)
            self.implant_node.save()

        # Handle Host Relationship
        # maybe move to a dedicated network func
        if self.host_node:
            if not self.implant_node.host.is_connected(self.host_node):
                # connect our implant, to our host
                self.implant_node.host.connect(self.host_node)
                server_logger.info("Implant linked to host")
            else:
                server_logger.debug("Implant already linked to host")

        # then call the network setup funcs
        self.populate_neo4j_with_implant_metadata()

        return self.implant_node

    def populate_neo4j_with_implant_metadata(self):
        self._check_network()
        self._check_network_gateway()
        self._check_network_to_gateway()

    def _check_network(self):
        """
        Function for network related nodes in neo4j
        """
        cidr_value = self.metadata.get("cidr", "10.0.0.0/24")

        # Safely get or create the network node
        net_node = Neo4jNetworkNode.get_or_create({"cidr": cidr_value})[0]

        # THE FIX: Connect the HOST to the network, not the implant!
        if getattr(self, "host_node", None):
            # Assuming your Neo4jHostNode model has 'connected_to = RelationshipTo("Neo4jNetworkNode", "CONNECTED_TO")'
            if not self.host_node.connected_to.is_connected(net_node):
                self.host_node.connected_to.connect(net_node)
                server_logger.info(
                    f"Linked Host ({self.host_node.address}) to Network ({cidr_value})"
                )
        else:
            server_logger.warning("No host available to link to the network.")

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
        implant_network_gateway_mac = self.metadata.get(
            "network_gateway_mac", "1.1.1.1"
        )

        if not implant_network_gateway:
            server_logger.warning("No network_gateway found for implant")
            return

        gw_node = Neo4jNetworkGatewayNode.nodes.get_or_none(
            host=implant_network_gateway, mac_address=implant_network_gateway_mac
        )
        if not gw_node:
            gw_node = Neo4jNetworkGatewayNode(
                host=implant_network_gateway, mac_address=implant_network_gateway_mac
            )
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
        implant_network_gateway_mac = self.metadata.get(
            "network_gateway_mac", "1.1.1.1"
        )

        # If we are missing either the cidr or ext ip we can't draw the link
        if not cidr_value or not implant_network_gateway:
            server_logger.warning(
                "Missing CIDR or implant_network_gateway; skipping network-to-gateway link."
            )
            return

        # Safely get or create BOTH nodes
        net_node = Neo4jNetworkNode.get_or_create({"cidr": cidr_value})[0]
        gw_node = Neo4jNetworkGatewayNode.get_or_create(
            {
                "host": implant_network_gateway,
                "mac_address": implant_network_gateway_mac,
            }
        )[0]

        # Connect them using the 'has_gateway' relationship defined on Neo4jNetworkNode
        # Check if they are already connected first to avoid duplicate relationship edges
        if not net_node.has_gateway.is_connected(gw_node):
            net_node.has_gateway.connect(gw_node)
            server_logger.info(
                f"Linked Network ({cidr_value}) -> Gateway ({implant_network_gateway})"
            )


class Neo4jHostNodeService:
    def __init__(self, address):
        self.address = address

        # setup logging for all funcs here
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(host=self.address)

    def register_host(self):
        # see if it exists
        node = Neo4jHostNode.find_existing(self.address)

        # if not, create it
        if not node:

            server_logger.info("Adding host to Neo4j")
            node = Neo4jHostNode(address=self.address).save()

        # Automatic Relationship Handling - later
        # network = NetworkManager.get_default_network()
        # node.connected_to.connect(network)

        # nuke all.
        structlog.contextvars.clear_contextvars()

        return node
