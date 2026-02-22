# neo4j functions
import logging

import structlog
from neomodel import db

from ..db.mysql_connector import get_mysql_session
from ..db.neo4j_models import (
    Neo4jC2ChannelNode,
    Neo4jHostNode,
    Neo4jImplantNode,
    Neo4jListenerNode,
    Neo4jMemstoreFileNode,
    Neo4jNetworkNode,
    Neo4jNicNode,
)
from .mysql_functions import ListenerService, MySQLImplantTaskService
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
        # Use Cypher MERGE to ensure atomicity at the DB level
        # TLDR, becaause we are using semi unstructured, duplicates are allowed by db.
        query = """
        MERGE (n:Neo4jImplantNode {implant_uuid: $implant_uuid})
        SET n += $props
        RETURN n
        """

        data_for_neo = kwargs.copy()
        del data_for_neo["nics"]  # tldr neo4j doenst like structured data.
        # This prevents the race condition where two threads check find_existing
        # at the same time and both see 'None'
        db.cypher_query(
            query, {"implant_uuid": self.implant_uuid, "props": data_for_neo}
        )

        # Refresh the local object reference
        self.implant_node = Neo4jImplantNode.nodes.get(implant_uuid=self.implant_uuid)

        hostname = kwargs.get("system_hostname")
        # the only auto linking/magic that happens here is linking our implant to a host, and linking our implant to a listener.
        self.connect_implant_to_listener(self.listener_uuid)
        self.connect_implant_to_host(hostname)

        # create NIC's and link to us
        nics = kwargs.get("nics", {})

        # data = {mac:{ip, cidr (ex,24), gateway},}
        for nic_mac_address, data in nics.items():
            # create our NIC
            Neo4jNicNodeService.create_or_get_node(mac_address=nic_mac_address)

            # link nic to our host
            nic_ip_address = data.get("ip")
            Neo4jNicNodeService.connect_nic_to_host(
                hostname, mac_address=nic_mac_address, ip_address=nic_ip_address
            )

            # link NIC to network, if we have data for it
            cidr = data.get("cidr")
            gateway = data.get("gateway")
            if cidr and gateway:
                network_segment = f"{gateway}/{cidr}"
                Neo4jNicNodeService.connect_nic_to_network(
                    network_segment, nic_mac_address
                )

    @staticmethod
    def create_or_get_node(implant_uuid):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic
        """
        implant_node = Neo4jImplantNode.find_existing(implant_uuid=implant_uuid)
        if not implant_node:
            implant_node = Neo4jImplantNode(implant_uuid=implant_uuid).save()
            neo4j_logger.info(f"New node created: {implant_uuid}")

        return implant_node

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
    def connect_implant_to_host(self, hostname):
        # connects this classes implant to the host based on ip address of that host

        # lookup host
        host_node = Neo4jHostNodeService.create_or_get_node(hostname=hostname)

        # now that we have that new host, connect *us* to *it*. order very important here

        # if we aren't already running on this host
        if not self.implant_node.running_on.is_connected(host_node):
            # add us to it
            self.implant_node.running_on.connect(host_node)

        neo4j_logger.info(f"Implant {self.implant_uuid} connected to host {hostname}")

    # funcs to replicate api func
    @staticmethod
    def get_all():
        """Gets all Neo4jImplantNode instances in the DB, returns their properties."""
        node_data, _ = db.cypher_query(
            "MATCH (h:Neo4jImplantNode) RETURN properties(h)"
        )
        return [row[0] for row in node_data]

        # need to take that, then get .properties, and return just properties

    @staticmethod
    def get_by_uuid(implant_uuid: str):
        node = Neo4jImplantNode.nodes.get_or_none(implant_uuid=implant_uuid)
        if not node:
            return None

        # again return only the properties
        return node.__properties__

    @staticmethod
    def update_by_uuid(implant_uuid: str, data: dict):
        # direct query to allow addtl fields that don't exist
        # to be added. Could change later for tightening it up
        query = """
        MATCH (n:Neo4jImplantNode {implant_uuid: $implant_uuid})
        SET n += $props
        RETURN properties(n)
        """

        results, _ = db.cypher_query(
            query, {"implant_uuid": implant_uuid, "props": data}
        )
        # no return to save some processing

    @staticmethod
    def delete_by_uuid(implant_uuid: str) -> bool:
        node = Neo4jImplantNode.nodes.get_or_none(implant_uuid=implant_uuid)
        if not node:
            return False  # node doesn't exist

        node.delete()
        return True

    def search_implants(search_term: str) -> list[dict]:
        """
        Search implants using a Full-Text Index.
        """
        # Use Lucene syntax. Adding '*' allows for partial matches if the term is incomplete.
        # Example: '192.168' becomes '192.168*'
        formatted_term = f"{search_term}*"

        query = """
        CALL db.index.fulltext.queryNodes("implant_search_index", $term) 
        YIELD node, score
        RETURN properties(node) AS props
        ORDER BY score DESC
        """

        # Using your existing db.cypher_query pattern
        results, _ = db.cypher_query(query, {"term": formatted_term})

        return [row[0] for row in results]


class Neo4jHostNodeService:
    def __init__(self, hostname):
        self.hostname = hostname

        # setup logging for all funcs here
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(host=self.ip_address)

    """
    Host can have:
     - A network its connected to
     - implants that connect to it
    
    """

    @staticmethod
    def create_or_get_node(hostname):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic
        """
        host_node = Neo4jHostNode.find_existing(hostname=hostname)
        if not host_node:
            host_node = Neo4jHostNode(hostname=hostname).save()
            neo4j_logger.info(f"New Host discovered: {hostname}")

        return host_node

    def register_host(self):
        # see if it exists
        node = Neo4jHostNode.find_existing(self.hostname)

        # if not, create it
        if not node:
            neo4j_logger.info("Adding host to Neo4j")
            node = Neo4jHostNode(hostname=self.hostname).save()

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


class Neo4jNicNodeService:
    @staticmethod
    def create_or_get_node(mac_address):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic
        """
        listener_node = Neo4jNicNode.find_existing(mac_address=mac_address)
        if not listener_node:
            listener_node = Neo4jNicNode(mac_address=mac_address).save()
            neo4j_logger.info(f"New nic node created: {mac_address}")

        return listener_node

    @staticmethod
    def connect_nic_to_host(hostname, mac_address: str, ip_address=""):
        """
        hostname: hostname of host to connect the nic to

        mac_address: mac address of the NIC connecting to a host
        ip_address (optional): ip_address of the NIC connecting to a host, if you have the IP for that nic
        """

        # create or get our NIC
        nic_node = Neo4jNicNodeService.create_or_get_node(mac_address)
        # add ip to it as well if we have it
        nic_node.ip_address = ip_address
        nic_node.save()

        # create or get host node
        host_node = Neo4jHostNodeService.create_or_get_node(hostname)

        # 3: link nic to host
        if not nic_node.attached_to.is_connected(host_node):
            nic_node.attached_to.connect(host_node)

        neo4j_logger.info(f"Nic -> host successful")

    @staticmethod
    def connect_nic_to_network(network_cidr, nic_mac_address: str):
        """"""

        # create or get our NIC
        nic_node = Neo4jNicNodeService.create_or_get_node(nic_mac_address)
        # create or get host node
        network_node = Neo4jNetworkNodeService.create_or_get_node(network_cidr)

        # 3: link nic to host
        if not nic_node.in_network.is_connected(network_node):
            nic_node.in_network.connect(network_node)

        neo4j_logger.info(f"Nic -> network successful")


class Neo4jNetworkNodeService:
    @staticmethod
    def create_or_get_node(network_cidr):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic
        """
        listener_node = Neo4jNetworkNode.find_existing(cidr=network_cidr)
        if not listener_node:
            listener_node = Neo4jNetworkNode(cidr=network_cidr).save()
            neo4j_logger.info(f"New network created: {network_cidr}")

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


class Neo4jMemstoreFileNodeService:
    @staticmethod
    def create_or_get_node(file_name):
        """
        Creates a node. Useful for getting a quick new node and letting this handle all
        the node logic
        """
        listener_node = Neo4jMemstoreFileNode.find_existing(file_name=file_name)
        if not listener_node:
            listener_node = Neo4jMemstoreFileNode(file_name=file_name).save()
            neo4j_logger.info(f"New memstore file node created: {file_name}")

        return listener_node

    @staticmethod
    def connect_memstore_file_to_implant(
        file_name, implant_uuid, file_hash_md5: str = ""
    ):
        """
        hostname: hostname of host to connect the nic to

        mac_address: mac address of the NIC connecting to a host
        ip_address (optional): ip_address of the NIC connecting to a host, if you have the IP for that nic

        file_hash_md5: (optional) md5 of file
        """

        # create or get our implant
        implant_node = Neo4jImplantNodeService.create_or_get_node(implant_uuid)
        # add ip to it as well if we have it

        # create or get our file
        memstore_file_node = Neo4jMemstoreFileNodeService.create_or_get_node(file_name)
        # add in hash
        memstore_file_node.md5 = file_hash_md5
        memstore_file_node.save()

        # 3: link file to implant
        if not memstore_file_node.stored_in.is_connected(implant_node):
            memstore_file_node.stored_in.connect(implant_node)

        neo4j_logger.info(f"Memstore file -> Implant successful")

    @staticmethod
    def get_all_files_nodes_for_implant(
        implant_uuid: str,
    ) -> list[Neo4jMemstoreFileNode]:
        implant_node = Neo4jImplantNode.nodes.get_or_none(implant_uuid=implant_uuid)

        if not implant_node:
            return []

        # note, the reverse rel allwos us jsut to do this
        return list(implant_node.memstore_files.all())
