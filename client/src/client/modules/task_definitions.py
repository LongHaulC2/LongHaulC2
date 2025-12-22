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
    TASK = "task"
    DATA = "data"
    ERROR = "error"
    # maybe add a PARSE_ERROR if needed later.


def task_tree(command, args):
    match command:
        case "cmd":
            try:
                task = Cmd(cli=args)
                return ResultType.TASK, task
            # if not all args are present, or there's a bug, this will bubble up and be put on screen
            except ParseError as e:
                return ResultType.ERROR, str(e)

        case "data_command":
            data = "somedata"
            return ResultType.DATA, data  # Use Enum for clarity

        case _:
            return ResultType.DATA, "Invalid command"  # Or some other response


@dataclass
class Cmd:
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
