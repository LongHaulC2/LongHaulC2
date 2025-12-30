from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ListenerCreate:
    listener_host: Optional[str] = None
    listener_port: Optional[int] = None


@dataclass
class ListenerUpdate:
    listener_host: Optional[str] = None
    listener_port: Optional[int] = None
