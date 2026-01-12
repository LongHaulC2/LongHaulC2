from dataclasses import dataclass
from enum import Enum

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
    TASK = "task"  # tasks are sent to server
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


def task_tree(command, args):
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
            # descriptions[-1](0, line)

            return (ResultType.LIST, descriptions)

        case "cmd":
            try:
                task = Cmd(cli=args)
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
class Cmd:
    """
    [placeholder command for dev] Run a command on the host via cmd.exe
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
            "task": "cmd",
            "data": {
                "cli": self.cli,
            },
        }


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
