import argparse
import inspect
import shlex
from enum import Enum

# Explicit imports from tasks.py to satisfy Ruff
from client.src.client.modules.task_definitions import (
    BofRunner,
    Cd,
    DiscoverNeighbors,
    Exit,
    FileDownload,
    FileUpload,
    Ls,
    MemStoreClear,
    MemStoreDelete,
    MemStoreDownload,
    MemStoreList,
    MemStoreUpload,
    ParseError,
    Sleep,
    StratActive,
    StratGet,
    StratList,
    StratPost,
    discover_cmds,
    execution_cmds,
    fs_cmds,
    mem_cmds,
    strat_cmds,
    system_cmds,
    terminal_helper_cmds,
)

# API call for history command
from .api_calls import get_implant_task_history


class ResultType(Enum):
    TASK = "task"
    TEXT = "text"
    ERROR = "error"
    LIST = "list"
    CLEAR = "clear"


class HelpException(Exception):
    """Raised to intercept help output and return as string."""

    pass


class C2Parser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)

    def print_help(self, file=None):  # noqa - file needed here for argparse
        raise HelpException(self.format_help())

    def error(self, message):
        raise ParseError(f"Argument parsing error: {message}\nUsage: {self.format_usage()}")

    def exit(self, status=0, message=None):  # noqa - status needed here for argparse
        if message:
            raise ParseError(message)


def get_short_help(cls) -> str:
    if not cls.__doc__:
        return ""
    return inspect.cleandoc(cls.__doc__).split("\n")[0]


def get_full_desc(cls) -> str:
    if not cls.__doc__:
        return ""
    return inspect.cleandoc(cls.__doc__)


def build_cli_parser(implant_uuid: str):
    root_parser = C2Parser(prog="", add_help=False)
    subparsers = root_parser.add_subparsers(dest="command", parser_class=C2Parser)

    # Basic Commands
    for cmd_cls, name in [(Cd, "cd"), (Ls, "ls"), (Sleep, "sleep")]:
        p = subparsers.add_parser(name, help=get_short_help(cmd_cls), description=get_full_desc(cmd_cls))
        if name == "cd" or name == "ls":
            p.add_argument("directory", nargs="?", default=".", metavar="<directory>")
            p.set_defaults(
                func=lambda args, c=cmd_cls: (
                    ResultType.TASK,
                    c(implant_uuid=implant_uuid, directory=args.directory).to_task(),
                )
            )
        elif name == "sleep":
            p.add_argument("sleep_time", nargs="?", default="", metavar="<sleep_time>")
            p.set_defaults(
                func=lambda args, c=cmd_cls: (
                    ResultType.TASK,
                    c(implant_uuid=implant_uuid, sleep_time=args.sleep_time).to_task(),
                )
            )

    subparsers.add_parser("exit", help=get_short_help(Exit)).set_defaults(
        func=lambda args: (ResultType.TASK, Exit(implant_uuid=implant_uuid).to_task())  # noqa - args needed for return
    )

    # Strat Nested
    strat_p = subparsers.add_parser("strat").add_subparsers(dest="strat_cmd", parser_class=C2Parser)
    strat_p.add_parser("list").set_defaults(
        func=lambda args: (ResultType.TASK, StratList(implant_uuid=implant_uuid).to_task())  # noqa - args needed for return
    )
    strat_p.add_parser("active").set_defaults(
        func=lambda args: (ResultType.TASK, StratActive(implant_uuid=implant_uuid).to_task())  # noqa - args needed for return
    )

    for mode, cls in [("post", StratPost), ("get", StratGet)]:
        sp = strat_p.add_parser(mode)
        sp.add_argument("strategy_name")
        sp.set_defaults(
            func=lambda args, c=cls: (
                ResultType.TASK,
                c(implant_uuid=implant_uuid, strategy_name=args.strategy_name).to_task(),
            )
        )

    # File Nested
    file_p = subparsers.add_parser("file").add_subparsers(dest="file_cmd", parser_class=C2Parser)
    fd = file_p.add_parser("download")
    fd.add_argument("file_path")
    fd.set_defaults(
        func=lambda args: (ResultType.TASK, FileDownload(implant_uuid=implant_uuid, file_path=args.file_path).to_task())
    )

    fu = file_p.add_parser("upload")
    fu.add_argument("file_path")
    fu.add_argument("file_contents")
    fu.set_defaults(
        func=lambda args: (
            ResultType.TASK,
            FileUpload(implant_uuid=implant_uuid, file_path=args.file_path, file_contents=args.file_contents).to_task(),
        )
    )

    # Memstore Nested
    mem_p = subparsers.add_parser("memstore").add_subparsers(dest="mem_cmd", parser_class=C2Parser)
    mem_p.add_parser("list").set_defaults(
        func=lambda args: (ResultType.TASK, MemStoreList(implant_uuid=implant_uuid).to_task())  # noqa - args needed for return
    )
    mem_p.add_parser("clear").set_defaults(
        func=lambda args: (ResultType.TASK, MemStoreClear(implant_uuid=implant_uuid).to_task())  # noqa - args needed for return
    )

    for action, cls in [("upload", MemStoreUpload), ("download", MemStoreDownload), ("delete", MemStoreDelete)]:
        mp = mem_p.add_parser(action)
        mp.add_argument("file_name")
        if action == "upload":
            mp.add_argument("file_contents")
        mp.set_defaults(
            func=lambda args, c=cls, a=action: (
                ResultType.TASK,
                c(
                    implant_uuid=implant_uuid,
                    file_name=args.file_name,
                    file_contents=args.file_contents if a == "upload" else None,
                ).to_task(),
            )
        )

    # BOF
    bof = subparsers.add_parser("bof")
    bof.add_argument("bof_contents")
    bof.add_argument("bof_args", nargs=argparse.REMAINDER)
    bof.set_defaults(
        func=lambda args: (
            ResultType.TASK,
            BofRunner(
                implant_uuid=implant_uuid, bof_contents=args.bof_contents, bof_args=" ".join(args.bof_args)
            ).to_task(),
        )
    )

    # Discover
    disc = subparsers.add_parser("discover").add_subparsers(dest="disc_cmd", parser_class=C2Parser)
    disc.add_parser("neighbors").set_defaults(
        func=lambda args: (ResultType.TASK, DiscoverNeighbors(implant_uuid=implant_uuid).to_task())  # noqa - args needed for return
    )

    return root_parser


async def task_tree(user_input, implant_uuid):
    try:
        split_args = shlex.split(user_input)
    except ValueError as e:
        return (ResultType.ERROR, f"Quote error: {str(e)}")
    if not split_args:
        return (ResultType.TEXT, "")

    base = split_args[0]
    if base == "history":
        data = await get_implant_task_history(implant_uuid)
        return (ResultType.LIST, ["-" * 50, "Task History"] + data.get("data", []) + ["-" * 50])

    if base == "help":
        if len(split_args) == 1:

            def fmt(h, cmds):
                return (
                    ["-" * len(h), h, "-" * len(h)]
                    + [f"{c.command_name: <18}: {get_short_help(c)}" for c in cmds]
                    + ["\n"]
                )

            out = ["-" * 50, "Implant Help Menu", "-" * 50, "\n"]
            for name, _class in [
                ("System", system_cmds),
                ("File System", fs_cmds),
                ("Memory", mem_cmds),
                ("Strategy", strat_cmds),
                ("Execution", execution_cmds),
            ]:
                out.extend(fmt(name, _class))
            return (ResultType.LIST, out)
        split_args = split_args[1:] + ["--help"]

    if base == "clear":
        return (ResultType.CLEAR, "")

    parser = build_cli_parser(implant_uuid)
    try:
        parsed = parser.parse_args(split_args)
        return parsed.func(parsed)
    except HelpException as h:
        return (ResultType.LIST, str(h).splitlines())
    except ParseError as pe:
        return (ResultType.ERROR, str(pe))
    except Exception as e:
        return (ResultType.ERROR, str(e))


def get_all_command_names(parser, current_path="") -> list[str]:
    """Recursively walks an argparse tree to extract commands and their expected arguments."""
    commands = []

    # Add the base command path (e.g., "file", "file upload")
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

    # If it's an "end-node" command (like 'upload' or 'ls'), grab its argument structure
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


def get_all_command_classes():
    return system_cmds + fs_cmds + mem_cmds + strat_cmds + execution_cmds + discover_cmds + terminal_helper_cmds
