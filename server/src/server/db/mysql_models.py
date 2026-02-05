from edwh_uuid7 import uuid7
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Computed,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import LONGBLOB, TINYBLOB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.inspection import inspect

Base = declarative_base()


# Define the Implant model
class Implant(Base):
    __tablename__ = "implants"
    # using bigint for 9 quadrillion potential agents. Int was "only" 2.4 billion.
    # id = Column(BigInteger, primary_key=True, autoincrement=True)
    # moving to uuid for implants.
    implant_uuid = Column(String(36), primary_key=True, default=lambda: str(uuid7()))
    external_ip = Column(String(45))  # IP (IPv4/IPv6)
    internal_ip = Column(String(45))
    listener = Column(Text)  # Can be IP or DNS
    user = Column(String(255))
    system_hostname = Column(String(255))
    notes = Column(Text)
    process = Column(String(255))
    pid = Column(Integer)
    arch = Column(String(50))
    last_checkin = Column(
        BigInteger
    )  # Time field to store last check-in time - moved to epoch instead of old HH:DD:SS
    sleep_value = Column(Integer)  # Sleep value (seconds)

    # fulltext index for easier searching with mysql
    __table_args__ = (
        Index(
            "fulltext_index",
            "implant_uuid",
            "external_ip",
            "internal_ip",
            "listener",
            "user",
            "system_hostname",
            "notes",
            "process",
            "arch",
            mysql_prefix="FULLTEXT",
        ),
    )

    def to_dict(self):
        """
        Turns each field into a dict.

        Can then use as such, after querying:

        ```
            implants = session.query(Implant).all()
            data = [i.to_dict() for i in implants]
        ```

        """
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}


class ImplantTask(Base):
    __tablename__ = "implant_tasks"

    implant_uuid = Column(String(36))
    task_uuid = Column(String(36), primary_key=True)
    task_request = Column(JSON, nullable=True)  # Task request data (dynamic JSON)
    task_response = Column(JSON, nullable=True)  # Task response data (dynamic JSON)

    # addtl options to consider later:
    # task status (e.g., 'pending', 'completed')
    # status = Column(String(100), nullable=True)

    # Add generated columns for full-text indexing because json can't be indexed by itself
    task_request_text = Column(
        String(255),
        Computed("JSON_UNQUOTE(JSON_EXTRACT(task_request, '$'))", persisted=True),
        nullable=True,
    )
    task_response_text = Column(
        String(255),
        Computed("JSON_UNQUOTE(JSON_EXTRACT(task_response, '$'))", persisted=True),
        nullable=True,
    )
    # Add a full-text index on task_request, task_response, and task_uuid
    __table_args__ = (
        Index(
            "fulltext_index",
            "task_request_text",
            "task_response_text",
            "task_uuid",
            "implant_uuid",  # search by implant, found it useful
            mysql_prefix="FULLTEXT",  # MySQL-specific
        ),
    )

    def to_dict(self):
        """
        Turns each field into a dict.
        """
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}


class Listener(Base):
    __tablename__ = "listeners"
    listener_uuid = Column(String(36), primary_key=True)

    listener_host = Column(
        String(256)
    )  # 256 is I hope long enough for now for a dns/host name...
    listener_port = Column(Integer)

    listener_type = Column(String(255))
    listener_name = Column(String(255))
    listener_notes = Column(Text)

    listener_active = Column(Boolean)

    listener_profile_name = Column(Text)  # Name of Malleable C2 profile
    listener_profile_contents = Column(Text)  # FULL malleablec2 profile

    # Adding UniqueConstraint to enforce unique combination of listener_host and listener_port
    __table_args__ = (
        UniqueConstraint(
            "listener_host", "listener_port", "listener_active", name="_host_port_uc"
        ),
    )

    def to_dict(self):
        """
        Turns each field into a dict.

        Can then use as such, after querying:

        ```
            implants = session.query(Implant).all()
            data = [i.to_dict() for i in implants]
        ```

        """
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}


class ImplantPayload(Base):
    __tablename__ = "implant_payloads"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    payload_hash = Column(TINYBLOB(16))  # md5 hash
    payload_bytes = Column(
        LONGBLOB
    )  # LONGBLOB is 4gb (massive, intentional for expandability)
    payload_source_code_bytes = Column(LONGBLOB)
    # payload_listener_uuid = Column(String(36))  # matches Listener model uuid

    payload_name = Column(Text)

    build_uuid = Column(String(36))  # uuid to track the build

    build_status = Column(Text)  # status of build

    def to_dict(self):
        """
        Turns each field into a dict.
        """
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
