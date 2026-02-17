from flask_restx import Namespace, Resource, fields

from ..instance import api


###################
# Helpers
####################
# if you have a list of dicts use this
def wrap_response_list(api, inner_model):
    """
    Dynamically creates a wrapper model with 'data', 'message', and 'status'.
    The model name is generated automatically (e.g., 'BuildItemWrapper').
    """
    name = f"{inner_model.name}Wrapper"
    return api.model(
        name,
        {
            "data": fields.List(fields.Nested(inner_model)),
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


# if a single dict is returned use this
def wrap_response_single(api, inner_model):
    """
    Dynamically creates a wrapper model with 'data', 'message', and 'status'.
    The model name is generated automatically (e.g., 'BuildItemWrapper').
    """
    name = f"{inner_model.name}Wrapper"
    return api.model(
        name,
        {
            "data": fields.Nested(inner_model),
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


###################
# Implants
####################
IMPLANT_POST_RESPONSE_ITEM_MODEL = api.model(
    "IMPLANT_POST_RESPONSE_ITEM_MODEL",
    {
        "uuid": fields.String(
            description="the UUID of the implant in the Database",
            example="00000000-0000-0000-0000-000000000000",
        ),
    },
)
# use single, only one item is returned
IMPLANT_POST_SUCCESS_MODEL = wrap_response_single(api, IMPLANT_POST_RESPONSE_ITEM_MODEL)
