import base64
from dataclasses import asdict, dataclass
from enum import Enum

from ..modules.api_calls import get_implant_task_history

"""
Testing task definitions here, so there's a structured way of handling tasks.


example of a cmd.exe task:

task = Cmd(cli="whoami /all")
cmd_task = cmd.to_task()

# now can send this off to the server to queue


How this bubbles down:

1. User inputs command.

2. Command is split into 2 parts, 1: command, and arguments.

3. Based on command, a class is chosen to handle it.

4. That class does further processing on the command,a nd its arguments, to get it in a task ready form.

5. If no parsing errors, command is converted into a task ready form, and returned with a ResultType.TASK.
    Calling func then sends to server

6. If parsing errors, command is returned with a ResultType.DATA, and an "invalid command" message is pushed to screen

"""


class ParseError(Exception):
    """Custom exception for Parse validation errors."""

    pass


class ResultType(Enum):
    TASK = "task"  # tasks are sent to server - this is a dict of the FULL task
    TEXT = "text"  # text is just dumped on screen
    ERROR = "error"  # errors are dumped on screen, without prepend, in orange/yellow
    LIST = "list"  # Lists, are parsed over and send one entry at a time on screen, with no terminal prepend
    # maybe add a PARSE_ERROR if needed later.


def get_description_of_dataclasses(dataclasses, fixed_width=None):
    descriptions = []

    if fixed_width:
        max_len = fixed_width
    elif dataclasses:
        # this is padding between command name and the desc
        max_len = max(len(cls.command_name) for cls in dataclasses) + 2
    else:
        max_len = 0

    # The command column width + 2 characters for the ": " separator
    padding = max_len + 2

    for cls in dataclasses:
        # Format: "commandname    : description..."
        description = f"{cls.command_name: <{max_len}}: {cls.__doc__.strip()}"

        if hasattr(cls, "command_structure"):
            for structure in cls.command_structure:
                description += f"\n{' ' * padding} > {structure}"
        descriptions.append(description)

    return descriptions


async def task_tree(command, args, implant_uuid):
    """Task tree for parsing commands, and formatting them.

    Args:
        command (_type_): _description_
        args (_type_): _description_
        implant_uuid (_type_): _description_

    Returns:
        _type_: _description_
    """
    match command:
        # special command
        case "help":
            all_command_classes = get_all_command_classes()
            # Use max length + 4 buffer for the colon alignment
            global_max_len = max(len(cls.command_name) for cls in all_command_classes) + 4

            # 3. Helper to format the group
            def format_group(header, cmd_list):
                # Get the command lines using the global width
                lines = get_description_of_dataclasses(cmd_list, fixed_width=global_max_len)

                # Return:
                # [Newline + Header Name]
                # [Underline (same length as header)]
                # [Command List...]
                return ["-" * len(header), f"\n{header}", "-" * len(header)] + lines

            final_output = []

            final_output.append("-" * 50)
            final_output.append("Implant Help Menu")
            final_output.append("-" * 50)

            final_output.extend(format_group("System", system_cmds))
            final_output.extend(format_group("File System", fs_cmds))
            final_output.extend(format_group("Memory Store", mem_cmds))
            final_output.extend(format_group("C2 Strategy", strat_cmds))
            final_output.extend(format_group("Execution", execution_cmds))
            final_output.extend(format_group("Discovery", discover_cmds))

            final_output.append("\n")

            return (ResultType.LIST, final_output)
        case "history":
            # add a json object for json dump, and a plaintext option (default)  for parsed output
            # uses this list to pull the docstrings from, and turn into a help menu

            task_history_dict: list = await get_implant_task_history(implant_uuid)
            task_history_list = task_history_dict.get("data")
            # add in barriers:
            line = "-" * 50
            task_history_list.insert(0, line)
            task_history_list.insert(1, "Task History")
            task_history_list.insert(2, line)

            # format options
            # print(args)
            # if args[1] == "json":
            #     return (ResultType.TEXT, "json")

            # get last item,
            task_history_list.insert(len(task_history_list) + 1, line)
            task_history_list.insert(
                len(task_history_list) + 2,
                "all tasks, some may be truncated due to 1000 line limit of this terminal.",
            )
            task_history_list.insert(len(task_history_list) + 3, line)

            return (ResultType.LIST, task_history_list)

        case "cd":
            try:
                task = Cd(implant_uuid=implant_uuid, directory=args).to_task()
                return (ResultType.TASK, task)
            # if not all args are present, or there's a bug, this will bubble up and be put on screen
            except ParseError as e:
                return (ResultType.ERROR, str(e))

        case "ls":
            try:
                task = Ls(implant_uuid=implant_uuid, directory=args).to_task()
                return (ResultType.TASK, task)
            # if not all args are present, or there's a bug, this will bubble up and be put on screen
            except ParseError as e:
                return (ResultType.ERROR, str(e))

        case "sleep":
            try:
                task = Sleep(implant_uuid=implant_uuid, sleep_time=args).to_task()
                return (ResultType.TASK, task)
            # if not all args are present, or there's a bug, this will bubble up and be put on screen
            except ParseError as e:
                return (ResultType.ERROR, str(e))

        case "strat":
            if args.startswith("post"):
                strategy_name = args[5:]  # Extract strategy name after "post "
                try:
                    task = StratPost(implant_uuid=implant_uuid, strategy_name=strategy_name).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))

            elif args.startswith("get"):
                strategy_name = args[4:]  # Extract strategy name after "get "
                try:
                    task = StratGet(implant_uuid=implant_uuid, strategy_name=strategy_name).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))

            elif args.startswith("list"):
                try:
                    task = StratList(implant_uuid=implant_uuid).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))

            elif args.startswith("active"):
                try:
                    task = StratActive(implant_uuid=implant_uuid).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))

            else:
                return (
                    ResultType.ERROR,
                    "Invalid strat command. Use `strat post <strategy_name>`, "
                    "`strat get <strategy_name>`, or `strat list`",
                )

        case "file":
            if args.startswith("download"):
                raw_args = args[9:]  # Extract file path after "download"
                args_list = raw_args.split()
                # The file path is the first argument after "download"
                file_path = args_list[0]

                try:
                    task = FileDownload(implant_uuid=implant_uuid, file_path=file_path).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))

            if args.startswith("upload"):
                raw_args = args[7:]  # Extract file path after "upload"
                args_list = raw_args.split()
                # The file path is the first argument after "download"
                file_path = args_list[0]
                # The file contents is the second argument after "upload"
                # replace " " with "" to remove any spaces that could be trailing/leading,
                # which may cause problems with base64 decoding
                file_contents = (args_list[1]).replace(" ", "")

                try:
                    task = FileUpload(
                        implant_uuid=implant_uuid,
                        file_path=file_path,
                        file_contents=file_contents,
                    ).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))
            else:
                return (
                    ResultType.ERROR,
                    "Invalid file command. Use `file upload <file_path>` or `file download <file_path>`",
                )

        case "memstore":
            if args.startswith("upload"):
                raw_args = args[7:]  # Extract file name after "upload"
                args_list = raw_args.split()
                # The file name is the first argument after "upload"
                file_name = args_list[0]
                # The file contents is the second argument after "upload"
                # replace " " with "" to remove any spaces that could be trailing/leading, which may cause
                # problems with base64 decoding
                file_contents = (args_list[1]).replace(" ", "")

                try:
                    task = MemStoreUpload(
                        implant_uuid=implant_uuid,
                        file_name=file_name.strip(),
                        file_contents=file_contents.strip(),
                    ).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))
            elif args.startswith("download"):
                raw_args = args[9:]  # Extract file name after "download"
                args_list = raw_args.split()
                # The file name is the first argument after "download"
                file_name = args_list[0]

                try:
                    task = MemStoreDownload(implant_uuid=implant_uuid, file_name=file_name).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))

            elif args.startswith("delete"):
                raw_args = args[7:]  # Extract file name after "delete"
                args_list = raw_args.split()
                # The file name is the first argument after "delete"
                file_name = args_list[0]

                try:
                    task = MemStoreDelete(implant_uuid=implant_uuid, file_name=file_name).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))

            elif args.startswith("clear"):
                try:
                    task = MemStoreClear(implant_uuid=implant_uuid).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))
            elif args.startswith("list"):
                try:
                    task = MemStoreList(implant_uuid=implant_uuid).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))

            else:
                return (
                    ResultType.ERROR,
                    "Invalid memstore command.",
                )

        case "bof":
            try:
                args = args.split()
                bof_bytes = args[0]  # either the bytes of the bof, *or* the *memstore_name
                bof_args = args[1:]  # the rest of the args are here.
                bof_args = "".join(bof_args)  # turn args into one str for now
                # this could get really ugly really quick, ex bof kfasldfjsdfjsakfjsa== myarg
                # or just do bof *mybof args

                # no args, args are just bof content, either in base64 or a memstore location
                task = BofRunner(implant_uuid=implant_uuid, bof_contents=bof_bytes, bof_args=bof_args).to_task()
                return (ResultType.TASK, task)

            except ParseError as e:
                return (ResultType.ERROR, str(e))

        case "discover":
            if args.startswith("neighbors"):
                task = DiscoverNeighbors(implant_uuid=implant_uuid).to_task()
                return (ResultType.TASK, task)

            else:
                return (
                    ResultType.ERROR,
                    "Invalid discover command.",
                )

        case "exit":
            try:
                task = Exit(implant_uuid=implant_uuid).to_task()
                return (ResultType.TASK, task)
            except ParseError as e:
                return (ResultType.ERROR, str(e))

        case _:
            return (ResultType.ERROR, "Invalid command")  # Or some other response


@dataclass(frozen=True)
class TaskDetail:
    task_name: str
    args: dict


@dataclass(frozen=True)
class Task:
    # task_uuid: str  # added by server
    implant_uuid: str
    task: TaskDetail


def create_and_verify_task(implant_uuid: str, task: TaskDetail):
    """Adds implant uuid to task, making it a "proper" task

    Args:
        implant_uuid (str): implant uuid
        task (dict): task dict: `{task: {'task_name':'task', 'args':{...}}}

    Returns:
        _type_: _description_
    """
    t = Task(implant_uuid=implant_uuid, task=task)
    task_as_dict = asdict(t)
    return task_as_dict


@dataclass(frozen=True)
class Cd:
    R"""
    Change the current working directory on the host.
    """

    command_name = "cd"
    command_structure = ["cd <directory>"]

    implant_uuid: str
    directory: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.directory:
            # Raise a ParseError exception if cli is None or empty
            raise ParseError("The 'dir' argument cannot be None or empty. Ex: `cd <cli arg>`: `cd C:\\Users\\`")

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"directory": self.directory}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class Sleep:
    R"""
    Set sleep timer on the host.
    """

    command_name = "sleep"
    command_structure = ["sleep <seconds>"]

    implant_uuid: str
    sleep_time: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.sleep_time:
            raise ParseError("The 'sleep_time' argument cannot be None or empty. Ex: `sleep <sleep_time>`: `sleep 5`")

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"sleep_time": int(self.sleep_time)}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class StratPost:
    R"""
    Set the post strategy for the implant.
    """

    command_name = "strat post"
    command_structure = ["strat post <post_strat_name>"]

    implant_uuid: str
    strategy_name: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.strategy_name:
            raise ParseError(
                "The 'strategy_name' argument cannot be None or empty. "
                "Ex: `strat post <strategy_name>`: `strat post my_post_strategy`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"strategy_name": self.strategy_name}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


class StratGet:
    R"""
    Set the get strategy for the implant.
    """

    command_name = "strat get"
    command_structure = ["strat get <get_strat_name>"]

    implant_uuid: str
    strategy_name: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.strategy_name:
            raise ParseError(
                "The 'strategy_name' argument cannot be None or empty. "
                "Ex: `strat get <strategy_name>`: `strat get my_get_strategy`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"strategy_name": self.strategy_name}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class StratList:
    R"""
    List the available strategies for the implant.
    """

    command_name = "strat list"

    implant_uuid: str

    # def __post_init__(self):
    #     """Automatically run something when the dataclass is created."""
    #     if not self.strategy_name:
    #         raise ParseError(
    #             "The 'strategy_name' argument cannot be None or empty.
    #               Ex: `strat get <strategy_name>`: `strat get my_get_strategy`"
    #         )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class StratActive:
    R"""
    List the active strategy for the implant.
    """

    command_name = "strat active"

    implant_uuid: str

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class FileDownload:
    R"""
    Get a file from the host the implant is running on.
    """

    command_name = "file download"
    command_structure = ["file download <file_path>"]

    implant_uuid: str
    file_path: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.file_path:
            raise ParseError(
                "The 'file_path' argument cannot be None or empty. "
                "Ex: `file download <file_path>`: `file download C:\\Users\\user\\file.txt`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"file_path": self.file_path}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class FileUpload:
    R"""
    Upload a file to the host the implant is running on.
    """

    command_name = "file upload"
    command_structure = [
        "file upload <file_save_path> <base64_file_contents>",
        "file upload <file_save_path> *<memstore_file_name>",
    ]
    implant_uuid: str
    file_path: str
    file_contents: str | bytes  # start with base64. figure out the upload button later

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.file_path:
            raise ParseError(
                "The 'file_path' argument cannot be None or empty. "
                "Ex: `file upload <file_path>`: `file upload C:\\Users\\user\\file.txt`"
            )
        if not self.file_contents:
            raise ParseError(
                "The 'file_contents' argument cannot be None or empty. "
                "Ex: `file upload <file_path>`: `file upload C:\\Users\\user\\file.txt`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""
        # convert from base64, to bytes, for easier CLI handling
        try:
            # option to pass in raw file contents. This is used by the upload buttons
            if isinstance(self.file_contents, bytes):
                task_args = {
                    "file_path": self.file_path,
                    "file_contents": self.file_contents,
                }

            # if file contents are not raw, aka, some form of text.
            else:
                # if user is trying to deref...
                # print(self.file_contents)
                if self.file_contents[0] == "*":
                    task_args = {
                        "file_path": self.file_path,
                        "file_contents": self.file_contents,
                    }
                # otherwise they are passing base64 data
                else:
                    bytes_file_contents = base64.b64decode(self.file_contents)
                    task_args = {
                        "file_path": self.file_path,
                        "file_contents": bytes_file_contents,
                    }

            task_detail = TaskDetail(task_name=self.command_name, args=task_args)
            final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
            return final_task
        except Exception:
            # likely base64 err. could  handle this better.
            raise ParseError


@dataclass(frozen=True)
class MemStoreUpload:
    R"""
    Upload a file to the implant memstore. Alternatively, use the file upload button.
    """

    command_name = "memstore upload"
    command_structure = ["memstore upload <file_name> <base64_file_contents>"]
    implant_uuid: str
    file_name: str
    file_contents: str | bytes  # start with base64. figure out the upload button later

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.file_name:
            raise ParseError(
                "The 'file_name' argument cannot be None or empty. "
                "Ex: `memstore upload <base64 data>`: `memstore upload aabbcc==`"
            )
        if not self.file_contents:
            raise ParseError(
                "The 'file_contents' argument cannot be None or empty. "
                "Ex: `memstore upload <base64 data>`: `memstore upload aabbcc==`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        # option to pass in raw file contents. This is used by the upload buttons
        if isinstance(self.file_contents, bytes):
            task_args = {
                "file_name": self.file_name,
                "file_contents": self.file_contents,
            }

        else:
            # convert from base64, to bytes, for easier CLI handling
            bytes_file_contents = base64.b64decode(self.file_contents)

            task_args = {
                "file_name": self.file_name,
                "file_contents": bytes_file_contents,
            }

        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class MemStoreDownload:
    R"""
    Download a file from the implant memory store.
    """

    command_name = "memstore download"
    command_structure = ["memstore download <file_name>"]

    implant_uuid: str
    file_name: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.file_name:
            raise ParseError(
                "The 'file_name' argument cannot be None or empty. Ex: `memstore download <file_name>`: "
                "`memstore download example.txt`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""
        # convert from base64, to bytes, for easier CLI handling

        task_args = {
            "file_name": self.file_name,
        }
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class MemStoreDelete:
    R"""
    Delete a file from the implants memory store.
    """

    command_name = "memstore delete"
    command_structure = ["memstore delete <file_name>"]
    implant_uuid: str
    file_name: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.file_name:
            raise ParseError(
                "The 'file_name' argument cannot be None or empty. Ex: `memstore delete <file_name>`: "
                "`memstore delete not_more_malware`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""
        # convert from base64, to bytes, for easier CLI handling

        task_args = {"file_name": self.file_name}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class MemStoreClear:
    R"""
    Clear *all* files in the implants memory store.
    """

    command_name = "memstore clear"
    implant_uuid: str

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""
        # convert from base64, to bytes, for easier CLI handling

        task_args = {}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class MemStoreList:
    R"""
    List all file names in the memstore.
    """

    command_name = "memstore list"
    implant_uuid: str

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""
        # convert from base64, to bytes, for easier CLI handling

        task_args = {}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class BofRunner:
    R"""
    Run a BOF.
    """

    command_name = "bof"
    command_structure = [
        "bof <base64_bof_object> <bof_args>",
        "bof *<memstore_bof_name> <bof_args>",
    ]

    implant_uuid: str
    # bof_name: str
    bof_contents: str | bytes  # start with base64. figure out the upload button later
    bof_args: str = ""

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""

        if not self.bof_contents:
            raise ParseError("The 'bof_contents' argument cannot be None or empty. Ex: `bof <base64>`: `bof aabbcc==`")

        # bof args might be none if no args
        # if not self.bof_args:
        #     raise ParseError(
        #         "The 'bof_args' argument cannot be None or empty. Ex: `bof <base64>`: `bof aabbcc==`"
        #     )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""
        # convert from base64, to bytes, for easier CLI handling
        try:
            # option to pass in raw file contents. This is used by the upload buttons
            if isinstance(self.bof_contents, bytes):
                task_args = {
                    "bof_contents": self.bof_contents,
                    "bof_args": self.bof_args,
                }

            # if file contents are not raw, aka, some form of text.
            else:
                # if user is trying to deref...
                # print(self.bof_contents)
                if self.bof_contents[0] == "*":
                    task_args = {
                        "bof_contents": self.bof_contents,
                        "bof_args": self.bof_args,
                    }
                # otherwise they are passing base64 data
                else:
                    bytes_file_contents = base64.b64decode(self.bof_contents)
                    task_args = {
                        "bof_contents": bytes_file_contents,
                        "bof_args": self.bof_args,
                    }

            task_detail = TaskDetail(task_name=self.command_name, args=task_args)
            final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
            return final_task
        except Exception:
            # likely base64 err. could  handle this better.
            raise ParseError


@dataclass(frozen=True)
class DiscoverNeighbors:
    R"""
    Discover neighbors via passive arp discovery, and resolves hostnames via `GetNameInfoW`. Results
    from this command are used to populate additional targets in the Graph
    """

    command_name = "discover neighbors"
    implant_uuid: str

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""
        # convert from base64, to bytes, for easier CLI handling
        try:
            task_detail = TaskDetail(task_name=self.command_name, args={})
            final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
            return final_task
        except Exception:
            raise ParseError


@dataclass(frozen=True)
class Exit:
    R"""
    Exit the implant. This will kill the implant process on the host, don't expect a response back from the
    implant with this command.
    """

    command_name = "exit"

    implant_uuid: str

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


@dataclass(frozen=True)
class Ls:
    R"""
    List the contents of a directory on the host.
    """

    command_name = "ls"

    implant_uuid: str
    directory: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.directory:
            # instead of throwing a parse error, just list "." if no directory is provided,
            #  which is more intuitive for ls because the dataclass is frozen, we have to use
            # object.__setattr__ to set the directory value to "." if it's not provided

            # kind of a hack, but it works for now. Keeps args protected as well.
            object.__setattr__(self, "directory", ".")

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"directory": self.directory}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(implant_uuid=self.implant_uuid, task=task_detail)
        return final_task


# List of system commands.
# TLDR, outside of function, easier to access across various functions

system_cmds = [Exit, Sleep]
fs_cmds = [Cd, Ls, FileDownload, FileUpload]
mem_cmds = [
    MemStoreList,
    MemStoreUpload,
    MemStoreDownload,
    MemStoreDelete,
    MemStoreClear,
]
strat_cmds = [StratActive, StratList, StratPost, StratGet]
execution_cmds = [BofRunner]
discover_cmds = [DiscoverNeighbors]


def get_all_command_classes():
    """
    Gets a list of all valid command clases for the CLI.
    """

    # get the longest command, use that as ref for spacing the :desc
    all_cmds = system_cmds + fs_cmds + mem_cmds + strat_cmds + execution_cmds + discover_cmds
    return all_cmds


def get_all_command_names():
    """
    Gets a list of all valid commands (ie. their text invokation) for the CLI.
    """
    cmd_classes = get_all_command_classes()
    cmd_list = []

    for cmd in cmd_classes:
        command_name = cmd.command_name

        # see if there's a command structure list for examples
        if hasattr(cmd, "command_structure"):
            command_structure = [cs for cs in cmd.command_structure]
            cmd_list.extend(command_structure)

        cmd_list.append(command_name)
    return cmd_list
