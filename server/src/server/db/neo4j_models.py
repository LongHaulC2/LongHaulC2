from neomodel import (
    BooleanProperty,
    IntegerProperty,
    RelationshipFrom,
    RelationshipTo,
    StringProperty,
    StructuredNode,
)
from neomodel.contrib import SemiStructuredNode


# semi structured for addtl ad hoc fields
class Neo4jImplantNode(SemiStructuredNode):
    """
    Implant Node for Implants.
    """

    implant_uuid = StringProperty(unique_index=True, required=True)

    connected_to = RelationshipTo("Neo4jNetworkNode", "CONNECTED_TO")


# for a host, who is not running an implant. I.e., was discovered. not sure if this is a good architecture idea yet, thinking, if a host -> an implant, how to handle.
class Neo4jHostNode(SemiStructuredNode):
    """
    Implant Node for Implants.
    """

    address = StringProperty(unique_index=True, required=True)
    # maybe get a mac in here too to prevent duplicates... can do with the passive discovery if it's altered

    connected_to = RelationshipTo("Neo4jNetworkNode", "CONNECTED_TO")

    # helper to find existing
    @classmethod
    def find_existing(cls, address=None, mac=None) -> object | None:
        """
        Custom logic to find a host by either IP or MAC.
        Useful for the 'Approval Queue' to suggest a Merge.
        """
        # if mac:
        #     node = cls.nodes.get_or_none(mac_address=mac)
        #     if node:
        #         return node

        if address:
            node = cls.nodes.get_or_none(address=address)
            if node:
                return node

        return None


# call when init?
class Neo4jNetworkNode(SemiStructuredNode):
    """
    Represents a Layer 3 network segment (subnet/VLAN).
    """

    cidr = StringProperty(unique_index=True, required=True)  # 10.0.1.0/24
    # name = StringProperty()
    # vlan_id = IntegerProperty()
    # description = StringProperty()

    # Relationships

    # the gateway this net connects to
    # Neo4jNetworkNode -> Neo4jNetworkNodeGateway
    has_gateway = RelationshipTo("Neo4jNetworkGatewayNode", "HAS_GATEWAY")

    # next hop (which is gateway)
    routed_from = RelationshipFrom("Neo4jNetworkGatewayNode", "ROUTES_TO")


class Neo4jNetworkGatewayNode(SemiStructuredNode):
    """
    Represents a routing-capable device (router/firewall/L3 switch).
    """

    # between host, and mac, this should be enough to differentiate
    # between diff networks. Can get this with ARP, if somewhat opsec safe.
    host = StringProperty(unique_index=True, required=True)
    mac_address = StringProperty(required=True)

    # hostname = StringProperty()
    # device_type = StringProperty()  # router, firewall, l3_switch
    external_exposed = BooleanProperty(default=False)  # can hit internet?

    # Relationships
    # what net connects to us
    serves_network = RelationshipFrom("Neo4jNetworkNode", "HAS_GATEWAY")

    # next hop/what other networks we connect to next, which could be a network
    routes_to = RelationshipTo("Neo4jNetworkNode", "ROUTES_TO")
