from typing import get_args

from flask_restx import fields

from ..db.neo4j_models import NodeType
from ..instance import api


###################
# Helpers
####################
def wrap_response_list(api, inner_model):
    name = f"{inner_model.name}Wrapper"
    return api.model(
        name,
        {
            "data": fields.List(fields.Nested(inner_model), default=[]),
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


def wrap_response_single(api, inner_model):
    name = f"{inner_model.name}Wrapper"
    return api.model(
        name,
        {
            "data": fields.Nested(inner_model, default={}),
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


def wrap_response_raw(api):
    name = "RawWrapper"
    return api.model(
        name,
        {
            "data": fields.Raw(),
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


def wrap_response_empty(api, model_name):
    """For responses that just return status/message (DELETE, PUT)"""
    return api.model(
        model_name,
        {
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


######################################################################
# Class: GraphSearch
# Routes: POST /graph/search
######################################################################

# POST /search
GRAPH_SEARCH_POST_INPUT = api.model(
    "GRAPH_SEARCH_POST_INPUT",
    {
        "search_term": fields.String(required=True, description="Term to search for."),
    },
)


# just give it a raw list to marshall with, we don't know exactly what the structure will look like
GRAPH_SEARCH_POST_RESPONSE = wrap_response_raw(api)

###################
# Types / Literals
####################
# pull the list of valid node types from the neo4j model class
NODE_TYPE_CHOICES = list(get_args(NodeType))

######################################################################
# Class: NodeParent & Node
# Routes: GET/POST /node/<nodename>/, GET/PATCH/DELETE /node/<nodename>/<uuid>
######################################################################

# generic wildcard for now. Will tighten down response structure later.
# NODE_GENERIC_MODEL = api.model(
#     "NODE_GENERIC_MODEL",
#     {
#         "*": fields.Raw(),
#     },
# )

# GET /node/<nodename>/
NODE_GET_LIST_RESPONSE = wrap_response_raw(api)

# GET /node/<nodename>/<uuid>
NODE_GET_SINGLE_RESPONSE = wrap_response_raw(api)

NODE_DELETE_RESPONSE = wrap_response_empty(api, "NODE_DELETE_RESPONSE_MODEL")

NODE_PATCH_INPUT = wrap_response_empty(api, "NODE_PATCH_INPUT_MODEL")


# Represents a single field's rules
SCHEMA_FIELD_MODEL = api.model(
    "SCHEMA_FIELD_MODEL",
    {
        "type": fields.String(example="StringProperty", description="The neomodel data type"),
        "required": fields.Boolean(example=True, description="Whether this field must be provided on POST"),
        "unique": fields.Boolean(example=False, description="Whether this field must be unique in the database"),
        "default_exists": fields.Boolean(
            example=False, description="Whether the database will auto-fill this if omitted"
        ),
    },
)

# The overall schema payload
NODE_SCHEMA_MODEL = api.model(
    "NODE_SCHEMA_MODEL",
    {
        "node_type": fields.String(example="implant"),
        "is_flexible": fields.Boolean(
            example=True, description="If true, the API accepts arbitrary fields not listed in the schema."
        ),
        "fields": fields.Raw(
            description="A dictionary mapping field names to their database rules.",
            example={
                "implant_uuid": {"type": "StringProperty", "required": True, "unique": True, "default_exists": False},
                "os_info": {"type": "StringProperty", "required": False, "unique": False, "default_exists": False},
            },
        ),
    },
)

NODE_SCHEMA_RESPONSE = wrap_response_single(api, NODE_SCHEMA_MODEL)
