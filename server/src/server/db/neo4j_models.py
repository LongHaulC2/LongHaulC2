from neomodel import StringProperty, StructuredNode
from neomodel.contrib import SemiStructuredNode


# semi structured for addtl ad hoc fields
class Neo4jImplant(SemiStructuredNode):
    """
    Implant Node for Implants.
    """

    implant_uuid = StringProperty(unique_index=True, required=True)
