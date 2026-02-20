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
