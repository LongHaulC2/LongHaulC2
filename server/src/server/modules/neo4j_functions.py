# neo4j functions
import logging

import structlog

from ..db.mysql_connector import get_mysql_session
from ..db.neo4j_models import (
    Neo4jC2ChannelNode,
    Neo4jHostNode,
    Neo4jImplantNode,
    Neo4jListenerNode,
    Neo4jNetworkNode,
)
from .mysql_functions import ImplantService, ListenerService, MySQLImplantTaskService
from .redis_functions import RedisImplantTaskService

neo4j_logger = logging.getLogger("neo4j_logger")

"""
each service class should have a:
 
@staticmethod
def create_or_get_node(args) -> object that returns model object:

"""


# NEW APPROACH, provide methods to hook things together, AVOID auto hooking, it makes things weird and not scalable
class Neo4jImplantNodeService:
    def __init__(self, implant_uuid, listener_uuid):
        self.implant_uuid = implant_uuid  # fed by listener
        self.listener_uuid = listener_uuid  # fed by listener
        self.metadata: dict
        self.implant_node = Neo4jImplantNode.find_existing(self.implant_uuid)

    """
    An implant can:

    - Connect to a host
    
    """
    # create node...

    def register_node(self, **kwargs):
        # Handle the implant node itself
        if not self.implant_node:
            self.implant_node = Neo4jImplantNode(
                implant_uuid=self.implant_uuid, **kwargs
            ).save()
        else:
            self._update_node(kwargs)

        # this is the only "magic" that occurs. Because implantuuid and listener uuid are req'd
        # we can hook them together automatically.
        self.connect_implant_to_listener(self.listener_uuid)

    def connect_implant_to_listener(self, listener_uuid):
        # connects this classes implant to a listener based on the listener UUID

        # 2 step process

        # 1: create listener node if not exist
        # 2: Create c2 channel node if not exist

        # create or get listener node
        listener_node = Neo4jListenerNodeService.create_or_get_node(listener_uuid)
        # create or get channel node
        c2_channel_node = Neo4jC2ChannelNodeService.create_or_get_node(listener_uuid)

        # 3: link implant -> c2 channel,
        # if we aren't already hooked up to the c2 channel, add us to it
        if not self.implant_node.c2_established.is_connected(c2_channel_node):
            self.implant_node.c2_established.connect(c2_channel_node)

        #  then c2 channel -> listener
        if not c2_channel_node.targets.is_connected(listener_node):
            c2_channel_node.targets.connect(listener_node)

        neo4j_logger.info(
            f"Implant {self.implant_uuid} connected to listener {self.listener_uuid}"
        )

    def _update_node(self, data: dict):
        for key, value in data.items():
            setattr(self.implant_node, key, value)
        self.implant_node.save()

    # call these for various things related to enrichement.
    # basically, have caller handle this, not automatically
    def connect_implant_to_host(self, host_ip_address):
        # connects this classes implant to the host based on ip address of that host

        # lookup host
        host_node = Neo4jHostNodeService.create_or_get_node(ip_address=host_ip_address)

        # now that we have that new host, connect *us* to *it*. order very important here

        # if we aren't already running on this host
        if not self.implant_node.running_on.is_connected(host_node):
            # add us to it
            self.implant_node.running_on.connect(host_node)

        neo4j_logger.info(
            f"Implant {self.implant_uuid} connected to host {host_ip_address}"
        )


class Neo4jHostNodeService:
    def __init__(self, ip_address):
        self.ip_address = ip_address

        # setup logging for all funcs here
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(host=self.ip_address)

    """
    Host can have:
     - A network its connected to
     - implants that connect to it
    
    """

    @staticmethod
    def create_or_get_node(ip_address):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic
        """
        host_node = Neo4jHostNode.find_existing(ip_address=ip_address)
        if not host_node:
            host_node = Neo4jHostNode(ip_address=ip_address).save()
            neo4j_logger.info(f"New Host discovered: {ip_address}")

        return host_node

    def register_host(self):
        # see if it exists
        node = Neo4jHostNode.find_existing(self.ip_address)

        # if not, create it
        if not node:
            neo4j_logger.info("Adding host to Neo4j")
            node = Neo4jHostNode(address=self.ip_address).save()

        # nuke all.
        structlog.contextvars.clear_contextvars()

        return node

        # idea. could check all networks in the db, and if our IP falls into the networks
        # range, we could add ourselves to it.


class Neo4jListenerNodeService:
    def __init__(self, listener_uuid):
        self.listener_uuid = listener_uuid

    @staticmethod
    def create_or_get_node(listener_uuid):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic
        """
        listener_node = Neo4jListenerNode.find_existing(listener_uuid=listener_uuid)
        if not listener_node:
            listener_node = Neo4jListenerNode(listener_uuid=listener_uuid).save()
            neo4j_logger.info(f"New listener node created: {listener_uuid}")

        return listener_node

    def register_listener(self, **kwargs):
        """
        Registers or updates a listener node.
        """
        # make sure it exsists....
        listener_node = Neo4jListenerNode.find_existing(self.listener_uuid)

        if not listener_node:
            neo4j_logger.info(f"Registering new Listener: {self.listener_uuid}")
            listener_node = Neo4jListenerNode(
                listener_uuid=self.listener_uuid, **kwargs
            ).save()
        else:
            neo4j_logger.debug(f"Updating existing Listener: {self.listener_uuid}")
            # Update dynamic properties (status, current connections, etc.)
            for key, value in kwargs.items():
                setattr(listener_node, key, value)
            listener_node.save()

        return listener_node


class Neo4jC2ChannelNodeService:
    # def __init__(self, listener_uuid):
    #     ...

    @staticmethod
    def create_or_get_node(listener_uuid) -> Neo4jC2ChannelNode:
        """
        Creates a node. This is a handy way to creat the nodes, especially if they have
        addtl logic that may require addtl lookups for their data
        """

        channel_id = Neo4jC2ChannelNodeService._get_channel_id(listener_uuid)

        listener_data = {}
        with get_mysql_session() as session:
            listener_class = ListenerService(session)
            listener_object = listener_class.get_by_id(listener_uuid)
            listener_data = listener_object.to_dict()

        listener_type = listener_data.get("listener_type", "")

        channel_node = Neo4jC2ChannelNode.find_existing(channel_id=channel_id)
        if not channel_node:

            channel_node = Neo4jC2ChannelNode(
                channel_id=channel_id, protocol=listener_type
            ).save()
            neo4j_logger.info(f"New c2 channel node created: {channel_id}")

        return channel_node

    @staticmethod
    def _get_channel_id(listener_uuid) -> str:
        """
        Create a unique key for the channel id in neo4j.
        """
        listener_data = {}
        with get_mysql_session() as session:
            listener_class = ListenerService(session)
            listener_object = listener_class.get_by_id(listener_uuid)
            listener_data = listener_object.to_dict()

        listener_type = listener_data.get("listener_type", "")
        listener_port = listener_data.get("listener_port", "")
        listener_host = listener_data.get("listener_host", "")

        channel_id = f"{listener_uuid}_{listener_type}_{listener_host}_{listener_port}"
        return channel_id
