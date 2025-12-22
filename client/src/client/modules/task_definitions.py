from dataclasses import dataclass
from enum import Enum

"""
Testing task definitions here, so there's a structured way of handling tasks.


example of a cmd.exe task:

task = Cmd(cli="whoami /all")
cmd_task = cmd.to_task()

# now can send this off to the server to queue

"""


class ResultType(Enum):
    TASK = "task"
    DATA = "data"


def task_tree(command, args):
    match command:
        case "cmd":
            task = Cmd(cli=args)
            return ResultType.TASK, task  # Use Enum for clarity

        case "data_command":
            data = "somedata"
            return ResultType.DATA, data  # Use Enum for clarity

        case _:
            return ResultType.DATA, "Invalid command"  # Or some other response


@dataclass
class Cmd:
    cli: str

    def to_task(self) -> dict:
        """Convert the dataclass to a task style dictionary structure."""
        return {
            "task": "cmd",
            "args": {
                "cli": self.cli,
            },
        }
