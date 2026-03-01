import argparse
import base64
import inspect
import shlex
from dataclasses import asdict, dataclass
from enum import Enum

from ..modules.api_calls import get_implant_task_history

'''
Notes:

Can add command examples with:

def get_epilog(cls) -> str:
    """Formats the dataclass examples list into a clean epilog string."""
    if hasattr(cls, 'examples') and cls.examples:
        return "Examples:\n  > " + "\n  > ".join(cls.examples)
    return ""

and

file_up = file_subs.add_parser(
        "upload",
        help=get_short_desc(FileUpload),
        epilog=get_epilog(FileUpload),  # add epliog call.
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

Then per class:

dataclass
MyClass:
    examples = ["abcd", "bcde"]

'''


class ResultType(Enum):
    TASK = "task"  # tasks are sent to server - this is a dict of the FULL task
    TEXT = "text"  # text is just dumped on screen
    ERROR = "error"  # errors are dumped on screen, without prepend, in orange/yellow
    LIST = "list"  # Lists, are parsed over and send one entry at a time on screen, with no terminal prepend
    # maybe add a PARSE_ERROR if needed later.
    CLEAR = "clear"  # Clear the terminal.


def get_short_help(cls) -> str:
    """Extracts just the first sentence of the docstring for the parent menu."""
    if not cls.__doc__:
        return ""
    clean_doc = inspect.cleandoc(cls.__doc__)
    # Split by newline and grab the first line to keep the parent help menu clean
    return clean_doc.split("\n")[0]


def get_full_desc(cls) -> str:
    """Extracts the entire cleaned docstring for the command's --help menu."""
    if not cls.__doc__:
        return ""
    return inspect.cleandoc(cls.__doc__)


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


class ParseError(Exception):
    """Custom exception for Parse validation errors."""

    pass


class HelpException(Exception):
    """Raised when a user requests help (-h/--help) to intercept stdout."""

    pass


class C2Parser(argparse.ArgumentParser):
    """
    Custom parser that intercepts help/errors and returns them
    as strings instead of calling sys.exit() and killing the CLI.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)

    def print_help(self, file=None):  # noqa: ARG002
        help_text = self.format_help()
        raise HelpException(help_text)

    def error(self, message):
        raise ParseError(f"Argument parsing error: {message}\nUsage: {self.format_usage()}")

    def exit(self, status=0, message=None):  # noqa: ARG002
        if message:
            raise ParseError(message)


def build_cli_parser(implant_uuid: str):
    root_parser = C2Parser(prog="", add_help=False)
    # parser_class=C2Parser ensures all subcommands inherit the silent/no-exit behavior
    subparsers = root_parser.add_subparsers(dest="command", parser_class=C2Parser)

    # ==========================================
    # System & File System Commands
    # ==========================================
    cd_parser = subparsers.add_parser(
        "cd",
        help=get_short_help(Cd),
        description=get_full_desc(Cd),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cd_parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        metavar="<directory>",
        help="The target directory path to navigate to (default: current directory).",
    )
    cd_parser.set_defaults(
        func=lambda args: (ResultType.TASK, Cd(implant_uuid=implant_uuid, directory=args.directory).to_task())
    )

    ls_parser = subparsers.add_parser(
        "ls",
        help=get_short_help(Ls),
        description=get_full_desc(Ls),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ls_parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        metavar="<directory>",
        help="The target directory to list contents for (default: current directory).",
    )
    ls_parser.set_defaults(
        func=lambda args: (ResultType.TASK, Ls(implant_uuid=implant_uuid, directory=args.directory).to_task())
    )

    sleep_parser = subparsers.add_parser(
        "sleep",
        help=get_short_help(Sleep),
        description=get_full_desc(Sleep),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sleep_parser.add_argument(
        "sleep_time",
        nargs="?",
        default="",
        metavar="<sleep_time>",
        help="The new sleep interval for the implant, in seconds.",
    )
    sleep_parser.set_defaults(
        func=lambda args: (ResultType.TASK, Sleep(implant_uuid=implant_uuid, sleep_time=args.sleep_time).to_task())
    )

    exit_parser = subparsers.add_parser(
        "exit",
        help=get_short_help(Exit),
        description=get_full_desc(Exit),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    exit_parser.set_defaults(func=lambda: (ResultType.TASK, Exit(implant_uuid=implant_uuid).to_task()))

    cheat_parser = subparsers.add_parser("cheatsheet", help="Show input formatting rules")

    def run_cheatsheet(args):  # noqa - args is req'd here due to argparse setup despite it not being used
        line = "-" * 50
        rules = [
            line,
            "Operator Input Cheatsheet",
            line,
            "1. SPACES: Wrap paths or arguments in double quotes.",
            '   Example: ls "C:\\Program Files"',
            "",
            "2. LEADING DASHES: Use '--' to stop the parser from interpreting data.",
            "   Example: bof *my_bof -- -Base64WithDash==",
            "",
            "3. QUOTES IN QUOTES: Use a backslash to escape internal quotes.",
            '   Example: bof *reg "HKLM\\Software\\"My App\\""',
            "",
            "4. TRAILING SLASHES: Avoid ending a quoted Windows path with a single backslash.",
            '   Wrong: "C:\\Users\\" -> Safe: "C:\\Users" or "C:\\Users\\\\"',
            line,
        ]
        return (ResultType.LIST, rules)

    cheat_parser.set_defaults(func=run_cheatsheet)

    # ==========================================
    # Nested Commands (Strat, File, Memstore, Discover)
    # ==========================================
    strat_parser = subparsers.add_parser("strat", help="C2 Strategy commands")
    strat_subs = strat_parser.add_subparsers(dest="strat_cmd", parser_class=C2Parser)

    strat_post = strat_subs.add_parser(
        "post",
        help=get_short_help(StratPost),
        description=get_full_desc(StratPost),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    strat_post.add_argument(
        "strategy_name",
        metavar="<strategy_name>",
        help="The name of the egress strategy to set for POST actions. Run `strat list` to get current strategies",
    )
    strat_post.set_defaults(
        func=lambda args: (
            ResultType.TASK,
            StratPost(implant_uuid=implant_uuid, strategy_name=args.strategy_name).to_task(),
        )
    )

    strat_get = strat_subs.add_parser(
        "get",
        help=get_short_help(StratGet),
        description=get_full_desc(StratGet),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    strat_get.add_argument(
        "strategy_name",
        metavar="<strategy_name>",
        help="The name of the egress strategy to set for GET actions. Run `strat list` to get current strategies",
    )
    strat_get.set_defaults(
        func=lambda args: (
            ResultType.TASK,
            StratGet(implant_uuid=implant_uuid, strategy_name=args.strategy_name).to_task(),
        )
    )

    strat_list = strat_subs.add_parser(
        "list",
        help=get_short_help(StratList),
        description=get_full_desc(StratList),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    strat_list.set_defaults(func=lambda: (ResultType.TASK, StratList(implant_uuid=implant_uuid).to_task()))

    strat_active = strat_subs.add_parser(
        "active",
        help=get_short_help(StratActive),
        description=get_full_desc(StratActive),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    strat_active.set_defaults(func=lambda: (ResultType.TASK, StratActive(implant_uuid=implant_uuid).to_task()))

    file_parser = subparsers.add_parser("file", help="File commands")
    file_subs = file_parser.add_subparsers(dest="file_cmd", parser_class=C2Parser)

    file_down = file_subs.add_parser(
        "download",
        help=get_short_help(FileDownload),
        description=get_full_desc(FileDownload),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    file_down.add_argument(
        "file_path",
        help=r"The path of the file to retrieve (ex: C:\secrets.txt).",
        metavar="<file_path>",
    )
    file_down.set_defaults(
        func=lambda args: (ResultType.TASK, FileDownload(implant_uuid=implant_uuid, file_path=args.file_path).to_task())
    )

    file_up = file_subs.add_parser(
        "upload",
        help=get_short_help(FileUpload),
        description=get_full_desc(FileUpload),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    file_up.add_argument(
        "file_path",
        help=r"The path that this file should be written to (ex: C:\Temp\not_malware.exe).",
        metavar="<file_path>",
    )
    file_up.add_argument(
        "file_contents",
        metavar="<base64 | *memstore_name>",
        help="The base64 encoded payload, OR a pointer to a memstore file (ex: *not_malware). There's a "
        "button for this too if you have a file on disk.",
    )
    file_up.set_defaults(
        func=lambda args: (
            ResultType.TASK,
            FileUpload(implant_uuid=implant_uuid, file_path=args.file_path, file_contents=args.file_contents).to_task(),
        )
    )

    mem_parser = subparsers.add_parser("memstore", help="Memstore commands")
    mem_subs = mem_parser.add_subparsers(dest="mem_cmd", parser_class=C2Parser)

    mem_up = mem_subs.add_parser(
        "upload",
        help=get_short_help(MemStoreUpload),
        description=get_full_desc(MemStoreUpload),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mem_up.add_argument(
        "file_name", metavar="<file_name>", help="The alias/name to assign this file inside the memstore."
    )
    mem_up.add_argument(
        "file_contents",
        metavar="<base64>",
        help="The base64 encoded payload to store in memory. There's a button for this too if you have a file on disk.",
    )
    mem_up.set_defaults(
        func=lambda args: (
            ResultType.TASK,
            MemStoreUpload(
                implant_uuid=implant_uuid, file_name=args.file_name, file_contents=args.file_contents
            ).to_task(),
        )
    )

    mem_down = mem_subs.add_parser(
        "download",
        help=get_short_help(MemStoreDownload),
        description=get_full_desc(MemStoreDownload),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mem_down.add_argument(
        "file_name", metavar="<file_name>", help="The name of the file to retrieve from the memstore."
    )
    mem_down.set_defaults(
        func=lambda args: (
            ResultType.TASK,
            MemStoreDownload(implant_uuid=implant_uuid, file_name=args.file_name).to_task(),
        )
    )

    mem_del = mem_subs.add_parser(
        "delete",
        help=get_short_help(MemStoreDelete),
        description=get_full_desc(MemStoreDelete),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mem_del.add_argument("file_name", metavar="<file_name>", help="The name of the file to delete from the memstore.")
    mem_del.set_defaults(
        func=lambda args: (
            ResultType.TASK,
            MemStoreDelete(implant_uuid=implant_uuid, file_name=args.file_name).to_task(),
        )
    )

    mem_clear = mem_subs.add_parser(
        "clear",
        help=get_short_help(MemStoreClear),
        description=get_full_desc(MemStoreClear),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mem_clear.set_defaults(func=lambda: (ResultType.TASK, MemStoreClear(implant_uuid=implant_uuid).to_task()))

    mem_list = mem_subs.add_parser(
        "list",
        help=get_short_help(MemStoreList),
        description=get_full_desc(MemStoreList),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mem_list.set_defaults(func=lambda: (ResultType.TASK, MemStoreList(implant_uuid=implant_uuid).to_task()))

    # ==========================================
    # Complex Commands (BOF)
    # ==========================================
    bof_parser = subparsers.add_parser(
        "bof",
        help=get_short_help(BofRunner),
        description=get_full_desc(BofRunner),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    bof_parser.add_argument(
        "bof_contents",
        metavar="<base64 | *memstore_name>",
        help="The BOF binary as base64 or a pointer to a memstore file.",
    )
    bof_parser.add_argument(
        "bof_args",
        nargs=argparse.REMAINDER,
        metavar="<args...>",
        help="Trailing arguments passed directly to the BOF runner, if the BOF takes arguments.",
    )
    bof_parser.set_defaults(
        func=lambda args: (
            ResultType.TASK,
            BofRunner(
                implant_uuid=implant_uuid, bof_contents=args.bof_contents, bof_args=" ".join(args.bof_args)
            ).to_task(),
        )
    )

    disc_parser = subparsers.add_parser("discover", help="Discover commands")
    disc_subs = disc_parser.add_subparsers(dest="disc_cmd", parser_class=C2Parser)

    disc_neigh = disc_subs.add_parser(
        "neighbors",
        help=get_short_help(DiscoverNeighbors),
        description=get_full_desc(DiscoverNeighbors),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Flags don't need metavars, argparse formats them as [--resolve] automatically
    disc_neigh.add_argument(
        "--resolve", action="store_true", help="Attempt to resolve hostnames for discovered IP addresses."
    )
    disc_neigh.set_defaults(
        func=lambda args: (
            ResultType.TASK,
            DiscoverNeighbors(implant_uuid=implant_uuid, resolve=args.resolve).to_task(),
        )
    )

    return root_parser


async def task_tree(user_input, implant_uuid):
    """Task tree for parsing commands, and formatting them."""

    try:
        # split the user intput into list, ex: ["ls", "C:\"]
        # use shelx here, instead of .split, shlex handles input like a unix term would

        split_args = shlex.split(user_input)
    except ValueError as e:
        return (ResultType.ERROR, f"Quote parsing error: {str(e)}")

    if not split_args:
        return (ResultType.TEXT, "")

    # grab the core command, the first one passed in
    base_command = split_args[0]

    # Intercept History (Due to async requirement)
    if base_command == "history":
        task_history_dict: list = await get_implant_task_history(implant_uuid)
        task_history_list = task_history_dict.get("data")
        line = "-" * 50
        task_history_list.insert(0, line)
        task_history_list.insert(1, "Task History")
        task_history_list.insert(2, line)
        task_history_list.insert(len(task_history_list) + 1, line)
        task_history_list.insert(
            len(task_history_list) + 2,
            "all tasks, some may be truncated due to 1000 line limit of this terminal.",
        )
        task_history_list.insert(len(task_history_list) + 3, line)
        return (ResultType.LIST, task_history_list)

    if base_command == "help":
        if len(split_args) == 1:
            # They just typed "help", show the custom grouped menu
            def get_short_desc(cls):
                return (
                    inspect.cleandoc(cls.__doc__).split("\n")[0] if getattr(cls, "__doc__", None) else "No description."
                )

            def format_group(header, cmd_list):
                lines = ["-" * len(header), header, "-" * len(header)]
                for cmd in cmd_list:
                    lines.append(f"{cmd.command_name: <18}: {get_short_desc(cmd)}")  # noqa: PERF401
                return lines + ["\n"]

            final_output = ["-" * 50, "Implant Help Menu", "-" * 50, "\n"]
            final_output.extend(format_group("System", system_cmds))
            final_output.extend(format_group("File System", fs_cmds))
            final_output.extend(format_group("Memory Store", mem_cmds))
            final_output.extend(format_group("C2 Strategy", strat_cmds))
            final_output.extend(format_group("Execution", execution_cmds))
            final_output.extend(format_group("Discovery", discover_cmds))
            final_output.extend(format_group("Terminal (local)", terminal_helper_cmds))
            return (ResultType.LIST, final_output)

        # if user types "help <somecommand>" turn it into "somecommand --help"
        split_args = split_args[1:] + ["--help"]

    if base_command == "clear":
        return (ResultType.CLEAR, "")

    # setup our parser
    parser = build_cli_parser(implant_uuid)

    try:
        parsed = parser.parse_args(split_args)

        # Failsafe if user types an incomplete command like just "strat"
        if not hasattr(parsed, "func"):
            return (
                ResultType.ERROR,
                f"Incomplete command '{parsed.command}'. Use '{parsed.command} --help' for usage.",
            )

        # Execute the specific Dataclass mapping
        return parsed.func(parsed)

    except HelpException as h:
        # hacky way to get to terminal without a "... >"
        # split help menu into a list, and say it's a list in return type, which will
        # not trigger the "...>"
        help_lines = str(h).splitlines()
        return (ResultType.LIST, help_lines)
    except ParseError as pe:
        return (ResultType.ERROR, str(pe))
    except Exception as e:
        return (ResultType.ERROR, str(e))


@dataclass(frozen=True)
class Cheatsheet:
    R"""
    Display the operator input rules for handling spaces, quotes, and dashes.
    """

    command_name = "cheatsheet"
    implant_uuid: str

    def to_task(self) -> dict:
        return {}


@dataclass(frozen=True)
class Help:
    R"""
    Displays the help menu for the commands
    """

    command_name = "help"
    implant_uuid: str

    def to_task(self) -> dict:
        return {}


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


@dataclass(frozen=True)
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
    Upload a file to the host the implant is running on, OR, write a file to disk from the memstore.
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
        except Exception as e:
            # likely base64 err. could  handle this better.
            raise ParseError from e


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
        except Exception as e:
            # likely base64 err. could  handle this better.
            raise ParseError from e


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
        except Exception as e:
            raise ParseError from e


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

terminal_helper_cmds = [Help, Cheatsheet]


def get_all_command_classes():
    """
    Gets a list of all valid command clases for the CLI.
    """

    # get the longest command, use that as ref for spacing the :desc
    all_cmds = system_cmds + fs_cmds + mem_cmds + strat_cmds + execution_cmds + discover_cmds + terminal_helper_cmds
    return all_cmds


# old way of doing this, which is fine,but takes more effort to keep classes up to date
# def get_all_command_names():
#     """
#     Gets a list of all valid commands (ie. their text invocation) for the CLI.
#     """
#     cmd_classes = get_all_command_classes()
#     cmd_list = []

#     for cmd in cmd_classes:
#         command_name = cmd.command_name

#         # see if there's a command structure list for examples
#         if hasattr(cmd, "command_structure"):
#             command_structure = [cs for cs in cmd.command_structure]
#             cmd_list.extend(command_structure)

#         cmd_list.append(command_name)
#     return cmd_list


def get_all_command_names(parser, current_path="") -> list[str]:
    """Recursively walks an argparse tree to extract commands and their expected arguments."""
    commands = []

    #  Add the base command path (e.g., "file", "file upload")
    if current_path:
        commands.append(current_path)

    has_subparsers = False

    # Look for nested commands
    if parser._subparsers:
        for action in parser._subparsers._group_actions:
            if isinstance(action, argparse._SubParsersAction):
                has_subparsers = True
                for cmd_name, subparser in action.choices.items():
                    full_cmd = f"{current_path} {cmd_name}".strip()
                    # Recursively dig down
                    commands.extend(get_all_command_names(subparser, full_cmd))

    #  If it's an "end-node" command (like 'upload' or 'ls'), grab its argument structure
    if not has_subparsers and current_path:
        # Get the native usage string
        raw_usage = parser.format_usage()

        # Clean it up for the UI dropdown
        clean_usage = raw_usage.replace("usage: ", "").replace("[-h]", "").strip()

        # Remove multiple spaces caused by stripping [-h]
        clean_usage = " ".join(clean_usage.split())

        # Add it to the autocomplete list if it has arguments
        if clean_usage and clean_usage != current_path:
            commands.append(clean_usage)

    return commands
