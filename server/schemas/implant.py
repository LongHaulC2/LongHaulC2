from dataclasses import dataclass

"""
Using dataclasses here for easier creation of correct data input to these functions below,
and it's easier to update for future fields.

Additionally, any unknown/extra keys throw an immediate error when the dataclass is being created:
`TypeError: ImplantUpdate.__init__() got an unexpected keyword argument 'urmom'`
This prevents any unintended fields from slipping through.
"""


# Explicitly does NOT have implant_uuid, as this is meant for the creation of implants. TLDR: DB adds the implant uuid,
# and if we had one here, this would overwrite it.
@dataclass
class ImplantCreate:
    external_ip: str | None = None
    # internal_ip: Optional[str] = None
    nics: list | None = None
    listener: str | None = None
    user: str | None = None
    system_hostname: str | None = None
    notes: str | None = None
    process: str | None = None
    pid: int | None = None
    arch: str | None = None
    last_checkin: int | None = None
    sleep_value: int | None = None
    # subnet_cidr: Optional[str] = None


@dataclass
class ImplantUpdate:
    implant_uuid: str
    external_ip: str | None = None
    # internal_ip: Optional[str] = None
    nics: list | None = None
    listener: str | None = None
    user: str | None = None
    system_hostname: str | None = None
    notes: str | None = None
    process: str | None = None
    pid: int | None = None
    arch: str | None = None
    last_checkin: int | None = None
    sleep_value: int | None = None


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


@dataclass
class TaskDetail:
    task_name: str
    args: dict


@dataclass
class Task:
    task_uuid: str  # added by server
    implant_uuid: str
    task: TaskDetail


@dataclass
class TaskResult:
    data_type: str  # Literal["text", "binary"] # if I waant to  validate an option
    data: str | bytes  # str or bytes here


@dataclass
class TaskResponse:
    task_uuid: str
    implant_uuid: int
    result: TaskResult


@dataclass
class ImplantMetadata:
    implant_uuid: str
    user: str
