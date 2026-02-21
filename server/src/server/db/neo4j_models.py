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

    ip_address = StringProperty(unique_index=True, required=True)

    # for addtl unique id if ever needed
    # mac_address = StringProperty()
    # hostname = StringProperty()

    # Host -> Network
    on_subnet = RelationshipTo("Neo4jNetworkNode", "ON_SUBNET")

    # things the host can see
    neighbors = RelationshipTo(
        "Neo4jHostNode", "DISCOVERED_VIA", model=DiscoveredViaRel
    )

    @classmethod
    def find_existing(cls, ip_address) -> object | None:
        """
        Custom logic to find a host by either IP or MAC.
        Useful for the 'Approval Queue' to suggest a Merge.
        """
        # if mac:
        #     node = cls.nodes.get_or_none(mac_address=mac)
        #     if node:
        #         return node

        if ip_address:
            node = cls.nodes.get_or_none(ip_address=ip_address)
            if node:
                return node

        return None


class Neo4jNetworkNode(SemiStructuredNode):
    """
    Represents a Layer 3 network segment (subnet/VLAN).
    """

    cidr = StringProperty(unique_index=True, required=True)  # 10.0.1.0/24
    # name = StringProperty()
    # vlan_id = IntegerProperty()
    # description = StringProperty()

    # Relationships
    routes_to = RelationshipTo("Neo4jNetworkNode", "ROUTES_TO")


class Neo4jListenerNode(SemiStructuredNode):
    """
    Listener Node for Listeners.
    """

    listener_uuid = StringProperty(unique_index=True, required=True)

    # listener_name = StringProperty()

    # connected_to = RelationshipTo("Neo4jNetworkNode", "CONNECTED_TO")
    # host = RelationshipFrom("Neo4jNetworkNode", "EGRESS")

    @classmethod
    def find_existing(cls, listener_uuid=None) -> "Neo4jListenerNode | None":
        """
        Lookup an implant by its unique UUID.
        """
        if listener_uuid:
            return cls.nodes.get_or_none(listener_uuid=listener_uuid)
        return None


class Neo4jC2ChannelNode(SemiStructuredNode):
    """
    Intermediate node representing the communication path.
    """

    channel_id = StringProperty(
        unique_index=True, required=True
    )  # e.g., session_id or protocol_host_hash
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
