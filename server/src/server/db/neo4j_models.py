from edwh_uuid7 import uuid7
from neomodel import (
    BooleanProperty,
    IntegerProperty,
    RelationshipFrom,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    StructuredRel,
)
from neomodel.contrib import SemiStructuredNode

"""
Overview:
Nodes:
 - Implant: Implant running
 - Network: represents one network
 - Host: Represents one host
 - c2_channel: represents the C2 channel
 - Listener: The listener we are calling back to


Labels (like tags/categories)
 - Internal (network)
 - External (network)
 - Airgapped (network)
 - gateway

Relationships:
 - RUNNING_ON: implant -[running_on]> host
 - ON_SUBNET: host to network, network to network
 - ROUTES_TO: network -> network


 for now, start with rel to (simplicity), then add rel_from later when advanced querying is needed.

 Upgrade: Every node will have a UUID7 assigned to it. This eliminates unique data problems and allows this to grow
 more. This should be the source of truth going forward for each item. If it's UUID is here, that is how it should
 be referred to, where possible, throughout the program


 """


class DiscoveredViaRel(StructuredRel):
    # What tool or protocol found this?ex, arp, icmp, etc.
    method = StringProperty(required=True)

    # Timestamp for aging out stale data later
    # first_seen = DateTimeProperty(default_now=True)
    # last_seen = DateTimeProperty(default_now=True)


# semi structured for addtl ad hoc fields
class Neo4jImplantNode(SemiStructuredNode):
    """
    Implant Node for Implants.
    """

    implant_uuid = StringProperty(unique_index=True, required=True)

    # implant -> host
    running_on = RelationshipTo("Neo4jHostNode", "RUNNING_ON")

    c2_established = RelationshipTo("Neo4jC2ChannelNode", "C2_ESTABLISHED")

    # inverse of stored in, this is from Memstore -> Implant
    memstore_files = RelationshipFrom("Neo4jMemstoreFileNode", "STORED_IN")

    # parent/child
    # later, involve c2 channel between these 2? could skip as well for simplicity...
    parent_to = RelationshipFrom("Neo4jImplantNode", "LINKED")
    child_of = RelationshipTo("Neo4jImplantNode", "LINKED")

    @classmethod
    def find_existing(cls, implant_uuid=None) -> "Neo4jImplantNode | None":
        """
        Lookup an implant by its unique UUID.
        """
        if implant_uuid:
            return cls.nodes.get_or_none(implant_uuid=implant_uuid)
        return None


class Neo4jHostNode(SemiStructuredNode):
    """
    Implant Node for Implants.
    """

    # default index
    host_uuid = StringProperty(unique_index=True, default=uuid7)

    # move me to *not* default.
    hostname = StringProperty(unique_index=True, required=True)

    # for addtl unique id if ever needed
    # mac_address = StringProperty()
    # hostname = StringProperty()

    # Host -> Network
    on_subnet = RelationshipTo("Neo4jNetworkNode", "ON_SUBNET")

    # things the host can see
    neighbors = RelationshipTo("Neo4jHostNode", "DISCOVERED_VIA", model=DiscoveredViaRel)

    # disk file -> host, inverse from the Neo4jFileNode
    stored_on = RelationshipFrom("Neo4jHostNode", "STORED_ON")

    @classmethod
    def find_existing(cls, hostname) -> object | None:
        """
        Custom logic to find a host by either IP or MAC.
        Useful for the 'Approval Queue' to suggest a Merge.
        """
        # if mac:
        #     node = cls.nodes.get_or_none(mac_address=mac)
        #     if node:
        #         return node

        if hostname:
            node = cls.nodes.get_or_none(hostname=hostname)
            if node:
                return node

        return None


class Neo4jNetworkNode(SemiStructuredNode):
    """
    Represents a Layer 3 network segment (subnet/VLAN).
    """

    network_uuid = StringProperty(unique_index=True, default=uuid7)

    # move me to not default
    cidr = StringProperty(unique_index=True, required=True)  # 10.0.1.0/24
    # name = StringProperty()
    # vlan_id = IntegerProperty()
    # description = StringProperty()

    # Relationships
    routes_to = RelationshipTo("Neo4jNetworkNode", "ROUTES_TO")

    @classmethod
    def find_existing(cls, cidr=cidr) -> "Neo4jC2ChannelNode | None":
        """
        Lookup an implant by its unique UUID.
        """
        if cidr:
            return cls.nodes.get_or_none(cidr=cidr)
        return None


# class Neo4jListenerNode(SemiStructuredNode):
#     """
#     Listener Node for Listeners.
#     """

#     uuid = StringProperty(unique_index=True, required=True)

#     # rest of fields are filled in by kwargs of register_listener
#     # listeners also curerntly live in the mysql db, they need to be transfered over to Neo4j at some point

#     # connected_to = RelationshipTo("Neo4jNetworkNode", "CONNECTED_TO")
#     # host = RelationshipFrom("Neo4jNetworkNode", "EGRESS")

#     @classmethod
#     def find_existing(cls, uuid=None) -> "Neo4jListenerNode | None":
#         """
#         Lookup an implant by its unique UUID.
#         """
#         if uuid:
#             return cls.nodes.get_or_none(uuid=uuid)
#         return None


class Neo4jListenerNode(StructuredNode):
    """
    Listener Node for Listeners. Strictly typed to mirror the MySQL schema.
    """

    listener_uuid = StringProperty(unique_index=True, required=True)

    # Core fields
    listener_host = StringProperty(max_length=256)
    listener_port = IntegerProperty()
    listener_type = StringProperty(max_length=255)
    listener_name = StringProperty(max_length=255)

    # Unlimited length text fields (equivalent to SQLAlchemy 'Text')
    listener_notes = StringProperty()

    # State
    listener_active = BooleanProperty(default=False)

    # Malleable C2 fields
    listener_profile_name = StringProperty()
    listener_profile_contents = StringProperty()

    # Relationships
    # connected_to = RelationshipTo("Neo4jNetworkNode", "CONNECTED_TO")
    # host = RelationshipFrom("Neo4jNetworkNode", "EGRESS")

    @classmethod
    def find_existing(cls, listener_uuid: str = None) -> "Neo4jListenerNode | None":
        """
        Lookup a listener by its unique UUID.
        """
        if listener_uuid:
            return cls.nodes.get_or_none(listener_uuid=listener_uuid)
        return None

    def to_dict(self) -> dict:
        """
        Serialize the node properties into a standard dictionary.

        Used by the API for getting listener data
        """
        return {
            "listener_uuid": self.listener_uuid,
            "listener_host": self.listener_host,
            "listener_port": self.listener_port,
            "listener_type": self.listener_type,
            "listener_name": self.listener_name,
            "listener_notes": self.listener_notes,
            "listener_active": self.listener_active,
            "listener_profile_name": self.listener_profile_name,
            "listener_profile_contents": self.listener_profile_contents,
        }


class Neo4jC2ChannelNode(SemiStructuredNode):
    """
    Intermediate node representing the communication path.
    """

    channel_uuid = StringProperty(unique_index=True, default=uuid7)

    channel_id = StringProperty(unique_index=True, required=True)  # e.g., session_id or protocol_host_hash
    protocol = StringProperty(required=True)  # "HTTPS", "DNS", "SMB"
    # jitter = IntegerProperty(default=0)
    # sleep = IntegerProperty(default=5)

    # Relationships
    # Implant -> our channel
    # implant = RelationshipFrom("Neo4jImplantNode", "ESTABLISHED")
    # Our Channel to Listener Node
    targets = RelationshipTo("Neo4jListenerNode", "TARGETS")

    # Our channel to Gateway
    # egress_point = RelationshipTo("Neo4jNetworkGatewayNode", "VIA_GATEWAY")
    @classmethod
    def find_existing(cls, channel_id=channel_id) -> "Neo4jC2ChannelNode | None":
        """
        Lookup an implant by its unique UUID.
        """
        if channel_id:
            return cls.nodes.get_or_none(channel_id=channel_id)
        return None


class Neo4jNicNode(SemiStructuredNode):
    implant_uuid = StringProperty(unique_index=True, default=uuid7)

    mac_address = StringProperty()
    ip_address = StringProperty()
    # associating hostname with NIC, as it's possible for this NIC's ip to be a different DNS name
    # than another NIC's IP's
    dns_name = StringProperty()
    # nic -> host
    attached_to = RelationshipTo("Neo4jHostNode", "ATTACHED_TO")
    # nic -> network
    in_network = RelationshipTo("Neo4jNetworkNode", "IN_NETWORK")

    @classmethod
    def find_existing(cls, mac_address=mac_address) -> "Neo4jC2ChannelNode | None":
        """
        Lookup an implant by its unique UUID.
        """
        if mac_address:
            return cls.nodes.get_or_none(mac_address=mac_address)
        return None


class Neo4jMemstoreFileNode(SemiStructuredNode):
    memstore_file_uuid = StringProperty(unique_index=True, default=uuid7)

    file_name = StringProperty(unique_index=True, required=True)

    # ip, optional
    # ip_address = StringProperty()
    # add hash?
    md5 = StringProperty()

    # memstore file -> implant
    stored_in = RelationshipTo("Neo4jImplantNode", "STORED_IN")

    @classmethod
    def find_existing(cls, file_name=file_name) -> "Neo4jMemstoreFileNode | None":
        """
        Lookup an implant by its unique UUID.
        """
        if file_name:
            return cls.nodes.get_or_none(file_name=file_name)
        return None


class Neo4jFileNode(SemiStructuredNode):
    file_uuid = StringProperty(unique_index=True, default=uuid7)

    file_path = StringProperty(unique_index=True, required=True)
    md5 = StringProperty()

    # disk file -> host
    stored_on = RelationshipTo("Neo4jHostNode", "STORED_ON")

    @classmethod
    def find_existing(cls, file_path=file_path) -> "Neo4jFileNode | None":
        """
        Lookup an implant by its unique UUID.
        """
        if file_path:
            return cls.nodes.get_or_none(file_path=file_path)
        return None
