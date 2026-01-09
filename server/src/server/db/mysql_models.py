from edwh_uuid7 import uuid7
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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

    # Primary key for the table
    # implant_uuid = Column(BigInteger, nullable=False)  # Links task to an agent
    implant_uuid = Column(String(36))
    task_uuid = Column(String(36), primary_key=True)

    # Columns for task request and response stored as JSON
    task_request = Column(JSON, nullable=True)  # Task request data (dynamic JSON)
    task_response = Column(JSON, nullable=True)  # Task response data (dynamic JSON)

    # Task type (e.g., 'scan', 'update') and task status (e.g., 'pending', 'completed')
    # task_type = Column(String(255), nullable=True)
    # status = Column(String(100), nullable=True)
    # due_date = Column(DateTime, nullable=True)  # Task due date, if relevant

    # __table_args__ = (
    #     Index(
    #         "fulltext_index",
    #         "task_request",
    #         "task_response",
    #         "task_uuid",
    #         mysql_prefix="FULLTEXT",
    #     ),
    # )

    def __repr__(self):
        return f"<AgentTask(id={self.id}, agent_id={self.agent_id}, task_type={self.task_type}, status={self.status})>"


"""
Usage:
Session = sessionmaker(bind=engine)
session = Session()

# Create a new task for a specific agent (agent_id = 1)
task1 = AgentTask(
    agent_id=1,
    task_type="scan",
    status="pending",
    task_request={"scan_details": "scan details here"},
    task_response=None
)

# Add and commit the task
session.add(task1)
session.commit()

# Close the session
session.close()

"""


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
    listener_profile = Column(Text)  # FULL malleablec2 profile

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
