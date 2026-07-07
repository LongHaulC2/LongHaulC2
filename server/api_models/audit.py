from flask_restx import fields

from ..instance import api

AUDIT_ENTRY_MODEL = api.model(
    "AuditEntry",
    {
        "id": fields.Integer(description="Entry ID"),
        "timestamp": fields.Integer(description="Unix timestamp (ms)"),
        "actor": fields.String(description="Username who performed the action"),
        "action": fields.String(description="Action performed"),
        "target_type": fields.String(description="Type of target (implant, listener, file, user)"),
        "target_uuid": fields.String(description="UUID of the target resource"),
        "detail": fields.String(description="Additional context"),
    },
)

AUDIT_PAGINATED_DATA = api.model(
    "AuditPaginatedData",
    {
        "entries": fields.List(fields.Nested(AUDIT_ENTRY_MODEL)),
        "total_count": fields.Integer(description="Total entries matching filters"),
        "limit": fields.Integer(description="Page size used"),
        "offset": fields.Integer(description="Offset used"),
    },
)

AUDIT_GET_RESPONSE = api.model(
    "AuditGetResponse",
    {
        "status": fields.String(example="200"),
        "message": fields.String(example="Success"),
        "data": fields.Nested(AUDIT_PAGINATED_DATA),
    },
)
