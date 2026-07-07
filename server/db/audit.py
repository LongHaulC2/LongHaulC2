import time

import structlog

from .mysql_connector import get_mysql_session
from .mysql_models import AuditLog

audit_logger = structlog.getLogger("server")


def log_audit(actor: str, action: str, target_type: str = "", target_uuid: str = "", detail: str = ""):
    try:
        with get_mysql_session() as session:
            entry = AuditLog(
                timestamp=int(time.time() * 1000),
                actor=actor,
                action=action,
                target_type=target_type or None,
                target_uuid=target_uuid or None,
                detail=detail or None,
            )
            session.add(entry)
    except Exception as e:
        audit_logger.warning("Failed to write audit log entry", error=str(e))


class MySQLAuditService:
    def __init__(self, session):
        self.session = session

    def _apply_filters(self, query, actor=None, action=None, target_type=None, since=None):
        if actor:
            query = query.filter(AuditLog.actor == actor)
        if action:
            query = query.filter(AuditLog.action == action)
        if target_type:
            query = query.filter(AuditLog.target_type == target_type)
        if since:
            query = query.filter(AuditLog.timestamp >= since)
        return query

    def get_entries(
        self,
        actor: str | None = None,
        action: str | None = None,
        target_type: str | None = None,
        since: int | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        query = self._apply_filters(
            self.session.query(AuditLog),
            actor=actor,
            action=action,
            target_type=target_type,
            since=since,
        )
        query = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
        return [entry.to_dict() for entry in query.all()]

    def count_entries(
        self,
        actor: str | None = None,
        action: str | None = None,
        target_type: str | None = None,
        since: int | None = None,
    ) -> int:
        from sqlalchemy import func

        query = self._apply_filters(
            self.session.query(func.count(AuditLog.id)),
            actor=actor,
            action=action,
            target_type=target_type,
            since=since,
        )
        return query.scalar()

    def get_all_entries(
        self,
        actor: str | None = None,
        action: str | None = None,
        target_type: str | None = None,
        since: int | None = None,
    ) -> list[dict]:
        query = self._apply_filters(
            self.session.query(AuditLog),
            actor=actor,
            action=action,
            target_type=target_type,
            since=since,
        )
        query = query.order_by(AuditLog.timestamp.desc())
        return [entry.to_dict() for entry in query.all()]
