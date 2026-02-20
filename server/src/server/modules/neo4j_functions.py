# neo4j functions
from ..db.mysql_connector import get_mysql_session
from ..db.neo4j_models import Neo4jImplant
from .mysql_functions import ImplantService, MySQLImplantTaskService
from .redis_functions import RedisImplantTaskService


def init_node(implant_uuid: str, **kwargs):
    """
    implant_uuid: prim key for implant_uuid
    kwargs: all things for metadata

    A function for initing a new node in neo4j

    makes it easier to just call thsi than call neo4j stuff a ton.

    adds in correlation to the node too


    """

    # get metadata from db (mysql is still source of truth for metadata)
    # implant_metadata = {}
    # with get_mysql_session() as session:
    #     implant_metadata = ImplantService(session)

    # unpack dict into neo4j implant to get all metadata
    new_implant = Neo4jImplant(implant_uuid=implant_uuid, **kwargs)
    new_implant.save()
