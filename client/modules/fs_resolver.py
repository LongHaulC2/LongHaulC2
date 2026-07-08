import structlog

from client.modules.api_calls import get_all_files, get_file_bytes

log = structlog.getLogger("fs_resolver")


async def resolve_fs_reference(arg: str) -> bytes:
    """Resolve an fs:<filename> reference to file bytes from the server filestore.

    Returns raw bytes on success. Raises ValueError if the file is not found.
    """
    filename = arg[3:]  # strip "fs:" prefix
    if not filename:
        raise ValueError("fs: prefix requires a filename (e.g. fs:mimikatz.exe)")

    all_files_resp = await get_all_files()
    files = (all_files_resp or {}).get("data", [])

    file_uuid = None
    for f in files:
        if f.get("file_name") == filename:
            file_uuid = f.get("file_uuid")
            break

    if not file_uuid:
        available = [f.get("file_name", "?") for f in files]
        raise ValueError(f"File '{filename}' not found in filestore. Available: {available}")

    content = await get_file_bytes(file_uuid)
    if not content:
        raise ValueError(f"Failed to download '{filename}' from filestore")

    log.info("Resolved fs: reference", filename=filename, size_bytes=len(content))
    return content


def is_fs_reference(arg: str) -> bool:
    return isinstance(arg, str) and arg.startswith("fs:")
