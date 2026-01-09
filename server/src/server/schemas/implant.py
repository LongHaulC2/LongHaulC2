from dataclasses import dataclass
from typing import Optional, Union

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


@dataclass
class Search:
    search_term: str


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


# Task Structure
"""
{
    "task_uuid": "1234", 
    "implant_uuid": "9999", 
    "task": 
        {
            "taskname":"cmd",
            "args":
                {
                    "cli":"whoami" # others...
                }
            }
        }

"""


@dataclass
class TaskArgs:
    cli: str


@dataclass
class TaskDetail:
    taskname: str
    args: TaskArgs


@dataclass
class Task:
    task_uuid: str  # added by server
    implant_uuid: str
    task: TaskDetail


# task response data class

"""
{
    "task_uuid":"", 
    "implant_uuid": "9999", 
    "result":
        {
            "data_type":"something,
            "data":"somedata"
        }
    }

"""


@dataclass
class TaskResult:
    data_type: str  # Literal["text", "binary"] # if I waant to  validate an option
    data: Union[str, bytes]  # str or bytes here


@dataclass
class TaskResponse:
    task_uuid: str
    implant_uuid: int
    result: TaskResult


# implant metadata
"""
{
    "implant_uuid":"1234"
}
"""


@dataclass
class ImplantMetadata:
    implant_uuid: str
