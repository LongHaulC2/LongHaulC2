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
from sqlalchemy.dialects.mysql import LONGBLOB, MEDIUMTEXT, TINYBLOB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import deferred

########################################
# Custom Base trial
########################################
"""
Trying something out, adding a "custom base" that has the to_dict method in it, so I don't have to add it to
all the individual models going forward.

This also leaves room for other methods going forward, if I want to add extra addons
"""


class CustomBase:
    def to_dict(self, include_deferred=False):
        """
        Turns each field into a dict.

        By default, this safely skips deferred columns (like LONGBLOBs, see model below)
        that haven't been loaded into memory yet, preventing accidental RAM exhaustion.
        """
        state = inspect(self)
        unloaded = state.unloaded

        result = {}
        for c in state.mapper.column_attrs:
            # If the column is unloaded (deferred) and we didn't explicitly ask for it, skip it.
            if not include_deferred and c.key in unloaded:
                continue

            result[c.key] = getattr(self, c.key)

        return result


Base = declarative_base(cls=CustomBase)
########################################


class Implant(Base):
    __tablename__ = "implants"
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
        # Standard B-Tree indexes for fast exact/prefix lookups
        Index("ix_implant_external_ip", "external_ip"),
        Index("ix_implant_internal_ip", "internal_ip"),
        # FULLTEXT index strictly for text-based natural language searching
        Index(
            "fulltext_index",
            "listener",
            "user",
            "system_hostname",
            "notes",
            "process",
            "arch",
            mysql_prefix="FULLTEXT",
        ),
    )


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
        MEDIUMTEXT,  # up to 16mb of text, should be enough for most requests, and allows for indexing. Can change to longtext if needed later, but that adds a lot of overhead.
        Computed("JSON_UNQUOTE(JSON_EXTRACT(task_request, '$'))", persisted=True),
        nullable=True,
    )
    task_response_text = Column(
        MEDIUMTEXT,  # up to 16mb of text, should be enough for most responses, and allows for indexing. Can change to longtext if needed later, but that adds a lot of overhead.
        Computed("JSON_UNQUOTE(JSON_EXTRACT(task_response, '$'))", persisted=True),
        nullable=True,
    )

    __table_args__ = (
        # Standard index to quickly find all tasks for a specific implant
        Index("ix_implanttask_implant_uuid", "implant_uuid"),
        # FULLTEXT strictly for the JSON text dumps
        Index(
            "fulltext_index",
            "task_request_text",
            "task_response_text",
            mysql_prefix="FULLTEXT",
        ),
        # add compression to the tasks, this is where the bulk of the data is
        # note... have to do "''" due to mysql being picky
        {"mysql_compression": "'zlib'"},
    )


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


class ImplantPayload(Base):
    __tablename__ = "implant_payloads"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    payload_hash = Column(TINYBLOB(16))  # md5 hash

    # using deffered here, waits until the field is explicity called before loading the data, otherwise we'll be querying lots of unneeded data at once
    # https://docs.sqlalchemy.org/en/14/orm/loading_columns.html
    payload_bytes = deferred(
        Column(LONGBLOB)
    )  # LONGBLOB is 4gb (massive, intentional for expandability)
    payload_source_code_bytes = deferred(Column(LONGBLOB))
    # payload_listener_uuid = Column(String(36))  # matches Listener model uuid

    payload_name = Column(Text)

    build_uuid = Column(String(36))  # uuid to track the build

    build_status = Column(Text)  # status of build

    __table_args__ = (
        # add payload compression, this is likely the 2nd largest data store, besides the task table
        # note... have to do "''" due to mysql being picky
        {"mysql_compression": "'zlib'"}
    )
