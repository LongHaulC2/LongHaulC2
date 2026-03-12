from flask_restx import fields

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
