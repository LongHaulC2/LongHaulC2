from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Time,
    BigInteger,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect

Base = declarative_base()


# Define the Implant model
class Implant(Base):
    __tablename__ = "implants"
    # using bigint for 9 quadrillion potential agents. Int was "only" 2.4 billion.
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    external_ip = Column(String(45))  # IP (IPv4/IPv6)
    internal_ip = Column(String(45))
    listener = Column(Text)  # Can be IP or DNS
    user = Column(String(255))
    system_hostname = Column(String(255))
    notes = Column(Text)
    process = Column(String(255))
    pid = Column(Integer)
    arch = Column(String(50))
    last_checkin = Column(BigInteger)  # Time field to store last check-in time - moved to epoch instead of old HH:DD:SS
    sleep_value = Column(Integer)  # Sleep value (seconds)

    def to_dict(self):
        '''
        Turns each field into a dict.

        Can then use as such, after querying:

        ```
            implants = session.query(Implant).all()
            data = [i.to_dict() for i in implants]
        ```

        '''
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
