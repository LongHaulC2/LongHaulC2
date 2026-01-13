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
    for cls in dataclasses:
        # Format the string as "classname_lower: docstring"
        description = f"{cls.__name__.lower()}: {cls.__doc__.strip()}"
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
            dataclasses = [Cmd, Powershell]
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

        case "cmd":
            try:
                task = Cmd(implant_uuid=implant_uuid, cli=args).to_task()
                return (ResultType.TASK, task)
            # if not all args are present, or there's a bug, this will bubble up and be put on screen
            except ParseError as e:
                return (ResultType.ERROR, str(e))

        case "data_command":
            data = "somedata"
            return (ResultType.TEXT, data)  # Use Enum for clarity

        case _:
            return (ResultType.ERROR, "Invalid command")  # Or some other response


@dataclass
class TaskDetail:
    taskname: str
    args: dict


@dataclass
class Task:
    # task_uuid: str  # added by server
    implant_uuid: str
    task: TaskDetail


def create_and_verify_task(implant_uuid: str, task: TaskDetail):
    """Adds implant uuid to task, making it a "proper" task

    Args:
        implant_uuid (str): implant uuid
        task (dict): task dict: `{task: {'taskname':'task', 'args':{...}}}

    Returns:
        _type_: _description_
    """
    t = Task(implant_uuid=implant_uuid, task=task)
    task_as_dict = asdict(t)
    return task_as_dict


@dataclass
class Cmd:
    """
    [placeholder command for dev] Run a command on the host via cmd.exe
    """

    implant_uuid: str
    cli: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.cli:
            # Raise a ParseError exception if cli is None or empty
            raise ParseError(
                "The 'cli' argument cannot be None or empty. Ex: `cmd <cli arg>`: `cmd whoami`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""

        task_args = {"cli": self.cli}
        task_detail = TaskDetail(taskname="cmd", args=task_args)

        final_task = create_and_verify_task(
            implant_uuid=self.implant_uuid, task=task_detail
        )
        return final_task
        # return task_detail


@dataclass
class Powershell:
    """
    [placeholder command for dev] Run a command on the host via powershell.exe. Ex: `powershell -c "<your_command>"`
    """

    cli: str

    def __post_init__(self):
        """Automatically run something when the dataclass is created."""
        if not self.cli:
            # Raise a ParseError exception if cli is None or empty
            raise ParseError(
                "The 'cli' argument cannot be None or empty. Ex: `cmd <cli arg>`: `cmd whoami`"
            )

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""
        return {
            "task": "powershell",
            "data": {
                "cli": self.cli,
            },
        }
