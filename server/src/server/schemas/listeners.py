from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ListenerCreate:
    listener_uuid: str
    listener_type: Optional[str] = None
    listener_host: Optional[str] = None
    listener_port: Optional[int] = None
    listener_name: Optional[str] = None
    listener_notes: Optional[str] = None
    # not required by api
    listener_active: Optional[bool] = None


# not currently used afaik
@dataclass
class ListenerUpdate:
    listener_host: Optional[str] = None
    listener_port: Optional[int] = None
