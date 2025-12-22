from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import time

"""
Using dataclasses here for easier creation of correct data input to these functions below,
and it's easier to update for future fields. 

Additionally, any unknown/extra keys throw an immediate error when the dataclass is being created:
`TypeError: ImplantUpdate.__init__() got an unexpected keyword argument 'urmom'`
This prevents any unintended fields from slipping through.
"""


@dataclass
class ImplantCreate:
    external_ip: Optional[str] = None
    internal_ip: Optional[str] = None
    listener: Optional[str] = None
    user: Optional[str] = None
    system_hostname: Optional[str] = None
    notes: Optional[str] = None
    process: Optional[str] = None
    pid: Optional[int] = None
    arch: Optional[str] = None
    last_checkin: Optional[int] = None
    sleep_value: Optional[int] = None


@dataclass
class ImplantUpdate:
    external_ip: Optional[str] = None
    internal_ip: Optional[str] = None
    listener: Optional[str] = None
    user: Optional[str] = None
    system_hostname: Optional[str] = None
    notes: Optional[str] = None
    process: Optional[str] = None
    pid: Optional[int] = None
    arch: Optional[str] = None
    last_checkin: Optional[int] = None
    sleep_value: Optional[int] = None


"""
Task data classes

Use as such:

task = Task(
    task="example_task",
    data=TaskData(
        some_var_1="",
        user="bob",
        hash="abc123"
    )
)

"""


@dataclass
class TaskData:
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    task: str
    data: TaskData
    uuid: str
