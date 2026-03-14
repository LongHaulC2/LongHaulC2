import base64
from dataclasses import asdict, dataclass

"""
Task definitions and supporting cast.

This is meant to be somewhat of a source of truth for the tasks,
and you can get a task, as a dict, via TaskClass.to_task(),
for sending to the server
"""


class ParseError(Exception):
    """Custom exception for Parse validation errors."""

    pass


@dataclass(frozen=True)
class TaskDetail:
    task_name: str
    args: dict


@dataclass(frozen=True)
class Task:
    implant_uuid: str
    task: TaskDetail


def create_and_verify_task(implant_uuid: str, task: TaskDetail):
    """Adds implant uuid to task, making it a 'proper' task."""
    t = Task(implant_uuid=implant_uuid, task=task)
    return asdict(t)


# ==========================================
# Task Dataclasses
# ==========================================


@dataclass(frozen=True)
class Cd:
    """Change the current working directory on the host."""

    command_name = "cd"
    command_structure = ["cd <directory>"]
    implant_uuid: str
    directory: str

    def __post_init__(self):
        if not self.directory:
            raise ParseError("The 'dir' argument cannot be empty. Ex: `cd C:\\Users\\` ")

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={"directory": self.directory})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class Ls:
    """List the contents of a directory on the host."""

    command_name = "ls"
    implant_uuid: str
    directory: str

    def __post_init__(self):
        if not self.directory:
            object.__setattr__(self, "directory", ".")

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={"directory": self.directory})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class Sleep:
    """Set sleep timer on the host."""

    command_name = "sleep"
    command_structure = ["sleep <seconds>"]
    implant_uuid: str
    sleep_time: str

    def __post_init__(self):
        if not self.sleep_time:
            raise ParseError("The 'sleep_time' argument cannot be empty. Ex: `sleep 5` ")

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={"sleep_time": int(self.sleep_time)})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class StratPost:
    """Set the post strategy for the implant."""

    command_name = "strat post"
    command_structure = ["strat post <post_strat_name>"]
    implant_uuid: str
    strategy_name: str

    def __post_init__(self):
        if not self.strategy_name:
            raise ParseError("strategy_name cannot be empty.")

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={"strategy_name": self.strategy_name})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class StratGet:
    """Set the get strategy for the implant."""

    command_name = "strat get"
    command_structure = ["strat get <get_strat_name>"]
    implant_uuid: str
    strategy_name: str

    def __post_init__(self):
        if not self.strategy_name:
            raise ParseError("strategy_name cannot be empty.")

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={"strategy_name": self.strategy_name})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class StratList:
    """List the available strategies for the implant."""

    command_name = "strat list"
    implant_uuid: str

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class StratActive:
    """List the active strategy for the implant."""

    command_name = "strat active"
    implant_uuid: str

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class FileDownload:
    """Get a file from the host the implant is running on."""

    command_name = "file download"
    command_structure = ["file download <file_path>"]
    implant_uuid: str
    file_path: str

    def __post_init__(self):
        if not self.file_path:
            raise ParseError("file_path cannot be empty.")

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={"file_path": self.file_path})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class FileUpload:
    """Upload a file to the host, or write a file to disk from the memstore."""

    command_name = "file upload"
    command_structure = ["file upload <save_path> <b64>", "file upload <save_path> *<mem_name>"]
    implant_uuid: str
    file_path: str
    file_contents: str | bytes

    def __post_init__(self):
        if not self.file_path or not self.file_contents:
            raise ParseError("Arguments cannot be empty.")

    def to_task(self) -> dict:
        if isinstance(self.file_contents, bytes) or self.file_contents.startswith("*"):
            task_args = {"file_path": self.file_path, "file_contents": self.file_contents}
        else:
            task_args = {"file_path": self.file_path, "file_contents": base64.b64decode(self.file_contents)}

        task_detail = TaskDetail(task_name=self.command_name, args=task_args)
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class MemStoreUpload:
    """Upload a file to the implant memstore."""

    command_name = "memstore upload"
    implant_uuid: str
    file_name: str
    file_contents: str | bytes

    def to_task(self) -> dict:
        contents = self.file_contents if isinstance(self.file_contents, bytes) else base64.b64decode(self.file_contents)
        task_detail = TaskDetail(
            task_name=self.command_name, args={"file_name": self.file_name, "file_contents": contents}
        )
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class MemStoreDownload:
    """Download a file from the implant memory store."""

    command_name = "memstore download"
    implant_uuid: str
    file_name: str

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={"file_name": self.file_name})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class MemStoreDelete:
    """Delete a file from the implants memory store."""

    command_name = "memstore delete"
    implant_uuid: str
    file_name: str

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={"file_name": self.file_name})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class MemStoreClear:
    """Clear *all* files in the implants memory store."""

    command_name = "memstore clear"
    implant_uuid: str

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class MemStoreList:
    """List all file names in the memstore."""

    command_name = "memstore list"
    implant_uuid: str

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class BofRunner:
    """Run a BOF."""

    command_name = "bof"
    implant_uuid: str
    bof_contents: str | bytes
    bof_args: str = ""

    def to_task(self) -> dict:
        if isinstance(self.bof_contents, bytes) or self.bof_contents.startswith("*"):
            contents = self.bof_contents
        else:
            contents = base64.b64decode(self.bof_contents)

        task_detail = TaskDetail(
            task_name=self.command_name, args={"bof_contents": contents, "bof_args": self.bof_args}
        )
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class DiscoverNeighbors:
    """Discover neighbors via passive arp discovery."""

    command_name = "discover neighbors"
    implant_uuid: str

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class Link:
    """Link to a child implant"""

    command_name = "link"
    implant_uuid: str
    protocol: str
    target_host: str | bytes

    # temp hardcoded
    inbox_pipe: str  # = "inbox2"
    outbox_pipe: str  # = "outbox2"
    # child_uuid: str | None = None

    async def to_task(self) -> dict:
        # get new impalnt uuid for linked implant
        # data_dict = await create_implant_entry(self.implant_uuid)

        # if not data_dict:
        #    raise RuntimeError(f"API request failed: Could not create child implant for {self.implant_uuid}")

        # child_uuid = data_dict.get("data", {}).get("uuid", {})
        # force set despite being frozen
        # object.__setattr__(self, "child_uuid", child_uuid)

        task_detail = TaskDetail(
            task_name=self.command_name,
            args={
                "protocol": self.protocol,
                "target": self.target_host,
                # "child_uuid": self.child_uuid,
                "inbox_pipe": self.inbox_pipe,
                "outbox_pipe": self.outbox_pipe,
            },
        )
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class Unlink:
    """Unlink from a child implant"""

    command_name = "unlink"
    implant_uuid: str
    protocol: str
    target_host: str | bytes

    def to_task(self) -> dict:
        task_detail = TaskDetail(
            task_name=self.command_name, args={"protocol": self.protocol, "target": self.target_host}
        )
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)

    # note - in future, need to do lookups for:
    # name of smb pipes
    # and we need to register a new implant that we will link *to*, to get a UUID for it


@dataclass(frozen=True)
class Exit:
    """Exit the implant and kill the process."""

    command_name = "exit"
    implant_uuid: str

    def to_task(self) -> dict:
        task_detail = TaskDetail(task_name=self.command_name, args={})
        return create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)


@dataclass(frozen=True)
class Cheatsheet:
    """Display the operator input rules."""

    command_name = "cheatsheet"
    implant_uuid: str

    def to_task(self) -> dict:
        return {}


@dataclass(frozen=True)
class Help:
    """Displays the help menu."""

    command_name = "help"
    implant_uuid: str

    def to_task(self) -> dict:
        return {}


# ==========================================
# Command Groups
# ==========================================

system_cmds = [Exit, Sleep]
fs_cmds = [Cd, Ls, FileDownload, FileUpload]
mem_cmds = [MemStoreList, MemStoreUpload, MemStoreDownload, MemStoreDelete, MemStoreClear]
strat_cmds = [StratActive, StratList, StratPost, StratGet]
execution_cmds = [BofRunner]
link_cmds = [Link, Unlink]
discover_cmds = [DiscoverNeighbors]
terminal_helper_cmds = [Help, Cheatsheet]
