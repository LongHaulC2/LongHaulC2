import csv
import datetime
import io

import structlog
from flask import Response, request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from ...api_models.audit import AUDIT_GET_RESPONSE
from ...api_models.error import COMMON_ERRORS
from ...db.audit import MySQLAuditService
from ...db.mysql_connector import get_mysql_session
from ...instance import api
from ...utils.response import APIResponse

audit_ns = Namespace("audit", description="Operator audit log")
api_logger = structlog.getLogger("api")


class AuditEntries(Resource):
    @jwt_required()
    @audit_ns.doc(
        summary="Get audit log entries",
        description="Retrieve audit log entries with optional filters and pagination.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
        params={
            "actor": {"description": "Filter by username", "in": "query"},
            "action": {"description": "Filter by action type", "in": "query"},
            "target_type": {"description": "Filter by target type", "in": "query"},
            "since": {"description": "Only entries after this timestamp (ms)", "in": "query"},
            "limit": {"description": "Max entries to return (default 50, max 1000)", "in": "query"},
            "offset": {"description": "Number of entries to skip (default 0)", "in": "query"},
        },
    )
    @audit_ns.response(200, "Audit entries retrieved", AUDIT_GET_RESPONSE)
    def get(self):
        """Retrieve audit log entries with optional filters and pagination."""
        actor = request.args.get("actor")
        action = request.args.get("action")
        target_type = request.args.get("target_type")
        since = request.args.get("since", type=int)
        limit = request.args.get("limit", default=50, type=int)
        offset = request.args.get("offset", default=0, type=int)

        limit = max(1, min(limit, 1000))
        offset = max(0, offset)

        with get_mysql_session() as session:
            svc = MySQLAuditService(session)
            entries = svc.get_entries(
                actor=actor,
                action=action,
                target_type=target_type,
                since=since,
                limit=limit,
                offset=offset,
            )
            total_count = svc.count_entries(
                actor=actor,
                action=action,
                target_type=target_type,
                since=since,
            )

        return APIResponse(
            status="200",
            message="Success",
            data={"entries": entries, "total_count": total_count, "limit": limit, "offset": offset},
        ).jsonify()


class AuditExport(Resource):
    @jwt_required()
    @audit_ns.doc(
        summary="Export full audit log as CSV",
        description="Download all audit entries matching filters as a CSV file.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
        params={
            "actor": {"description": "Filter by username", "in": "query"},
            "action": {"description": "Filter by action type", "in": "query"},
            "target_type": {"description": "Filter by target type", "in": "query"},
            "since": {"description": "Only entries after this timestamp (ms)", "in": "query"},
        },
    )
    def get(self):
        """Export all audit entries as CSV."""
        actor = request.args.get("actor")
        action = request.args.get("action")
        target_type = request.args.get("target_type")
        since = request.args.get("since", type=int)

        with get_mysql_session() as session:
            svc = MySQLAuditService(session)
            entries = svc.get_all_entries(
                actor=actor,
                action=action,
                target_type=target_type,
                since=since,
            )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "actor", "action", "target_type", "target_uuid", "detail"])

        for entry in entries:
            ts = entry.get("timestamp", 0)
            ts_str = datetime.datetime.fromtimestamp(ts / 1000, tz=datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow(
                [
                    ts_str,
                    entry.get("actor", ""),
                    entry.get("action", ""),
                    entry.get("target_type", ""),
                    entry.get("target_uuid", ""),
                    entry.get("detail", ""),
                ]
            )

        filename = f"audit_log_{datetime.datetime.now(tz=datetime.UTC).strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )


audit_ns.add_resource(AuditEntries, "/")
audit_ns.add_resource(AuditExport, "/export")

api.add_namespace(audit_ns)
