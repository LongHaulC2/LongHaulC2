from pathlib import Path
from typing import Dict, List, Optional, TypedDict, Union

# usigng TypedDicts to define structured data types for the implant builder module, which makes everything clearer and easier to manage.


class ListenerProfile(TypedDict):
    """Represents the raw data coming from the MySQL ListenerService."""

    listener_uuid: str
    listener_host: str
    listener_port: int
    listener_type: str  # e.g., 'http', 'smb'
    listener_name: str
    listener_active: bool
    listener_profile_name: str
    listener_profile_contents: str  # The raw malleable C2 profile text


# what the API sends in
class BuildRequestListener(TypedDict):
    # profile_get: str
    # profile_post: str
    listener_profile_name: str


class FunctionMapping(TypedDict):
    """Used in render.py to map C++ function names for polymorphism."""

    key: str  # The sanitized name used in the map
    value: str  # The actual C++ function name


class BuildJobConfig(TypedDict):
    """The master configuration object passed to the build process."""

    implant_name: str
    build_uuid: str
    # Maps listener_uuid -> ListenerProfile
    listeners: Dict[str, ListenerProfile]
    init_get_profile_uuid: str
    init_post_profile_uuid: str
