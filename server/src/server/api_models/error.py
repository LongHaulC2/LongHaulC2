from flask_restx import fields

from ..instance import api

ERROR_MODEL = api.model(
    "ErrorResponse",
    {
        "status": fields.String(example="400", description="The HTTP error code"),
        "message": fields.String(description="The error message", example="Resource not found"),
        "data": fields.Raw(description="Extra error details", example=""),
    },
)

# used for generic err handle, in the api.doc
COMMON_ERRORS = {
    400: ("Bad Request", ERROR_MODEL),
    404: ("Not Found", ERROR_MODEL),
    500: ("Internal Server Error", ERROR_MODEL),
}
