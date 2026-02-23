from dataclasses import dataclass


@dataclass
class ListenerCreate:
    listener_uuid: str
    listener_type: str | None = None
    listener_host: str | None = None
    listener_port: int | None = None
    listener_name: str | None = None
    listener_notes: str | None = None
    listener_profile_name: str | None = None
    listener_profile_contents: str | None = None
    # not required by api
    listener_active: bool | None = None


# not currently used afaik
@dataclass
class ListenerUpdate:
    listener_host: str | None = None
    listener_port: int | None = None
