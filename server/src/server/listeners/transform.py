import base64
import logging
import re

from ..utils.checks import check_type

server_logger = logging.getLogger("listener")

"""
This is for Data Transform Language
https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_profile-language.htm#_Toc65482837 (Data Transform Language))
"""


def transform_prepend(data: bytes, value) -> bytes:
    check_type(data, bytes, "data")

    try:
        b = value if isinstance(value, bytes) else malleable_string_to_bytes(value)
        return b + data
    except Exception as e:
        server_logger.exception("Error in transform_prepend")
        raise ValueError(f"Error in transform_prepend: {e}")


def undo_transform_prepend(data: bytes, value) -> bytes:
    """
    data: The bytes that *were* prepended, and are now getting removed
    """
    check_type(data, bytes, "data")

    try:
        b = value if isinstance(value, bytes) else malleable_string_to_bytes(value)
        return data[len(b) :]
    except Exception as e:
        server_logger.exception("Error in undo_transform_prepend")
        raise ValueError(f"Error in undo_transform_prepend: {e}")


def transform_append(data: bytes, value) -> bytes:
    check_type(data, bytes, "data")

    try:
        b = value if isinstance(value, bytes) else malleable_string_to_bytes(value)
        return data + b
    except Exception as e:
        server_logger.exception("Error in transform_append")
        raise ValueError(f"Error in transform_append: {e}")


def undo_transform_append(data: bytes, value) -> bytes:
    """
    data: The bytes that *were* appended, and are now getting removed
    """
    check_type(data, bytes, "data")

    try:
        b = value if isinstance(value, bytes) else malleable_string_to_bytes(value)
        return data[: -len(b)]
    except Exception as e:
        server_logger.exception("Error in undo_transform_append")
        raise ValueError(f"Error in undo_transform_append: {e}")


def base64_encode(data: bytes) -> bytes:
    check_type(data, bytes, "data")

    try:
        server_logger.debug("Base64 Encode input: %r", data)
        out = base64.b64encode(data)
        server_logger.debug("Base64 Encode output: %r", out)
        return out
    except Exception as e:
        server_logger.exception("Error in base64_encode")
        raise ValueError(f"Error in base64_encode: {e}")


def base64_decode(data: bytes) -> bytes:
    check_type(data, bytes, "data")

    try:
        server_logger.debug("Base64 Decode input: %r", data)
        out = base64.b64decode(data)
        server_logger.debug("Base64 Decode output: %r", out)
        return out
    except Exception as e:
        server_logger.exception("Error in base64_decode")
        raise ValueError(f"Error in base64_decode: {e}")


def base64url_encode(data: bytes) -> bytes:
    check_type(data, bytes, "data")

    try:
        server_logger.debug("Base64URL Encode input: %r", data)
        out = base64.urlsafe_b64encode(data).rstrip(b"=")
        server_logger.debug("Base64URL Encode output: %r", out)
        return out
    except Exception as e:
        server_logger.exception("Error in base64url_encode")
        raise ValueError(f"Error in base64url_encode: {e}")


def base64url_decode(data: bytes) -> bytes:
    check_type(data, bytes, "data")

    try:
        # force bytes if someone passes str
        if isinstance(data, str):
            server_logger.warning("Data was passed as str, converting to bytes.")
            data = data.encode()  # default UTF-8

        server_logger.debug("Base64URL Decode input: %r", data)

        padding = b"=" * (-len(data) % 4)
        out = base64.urlsafe_b64decode(data + padding)
        server_logger.debug("Base64URL Decode output: %r", out)
        return out
    except Exception as e:
        server_logger.exception("Error in base64url_decode")
        raise ValueError(f"Error in base64url_decode: {e}")


def xor_mask(data: bytes, key: bytes) -> bytes:
    check_type(data, bytes, "data")
    check_type(key, bytes, "bytes")

    try:
        server_logger.debug("XOR Mask input: data=%r key=%r", data, key)
        if not key:
            raise ValueError("Key must not be empty")

        out = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        server_logger.debug("XOR Mask output: %r", out)
        return out
    except Exception as e:
        server_logger.exception("Error in xor_mask")
        raise ValueError(f"Error in xor_mask: {e}")


def netbios_encode(data: bytes) -> bytes:
    check_type(data, bytes, "data")

    try:
        server_logger.debug("NetBIOS Encode input: %r", data)
        out = bytearray()

        for b in data:
            high = (b >> 4) & 0x0F
            low = b & 0x0F
            out.append(ord("a") + high)
            out.append(ord("a") + low)

        out_bytes = bytes(out)
        server_logger.debug("NetBIOS Encode output: %r", out_bytes)
        return out_bytes
    except Exception as e:
        server_logger.exception("Error in netbios_encode")
        raise ValueError(f"Error in netbios_encode: {e}")


def netbios_decode(data: bytes) -> bytes:
    check_type(data, bytes, "data")

    try:
        server_logger.debug("NetBIOS Decode input: %r", data)
        if len(data) % 2 != 0:
            raise ValueError("Invalid NetBIOS data length")

        out = bytearray()

        for i in range(0, len(data), 2):
            high = data[i] - ord("a")
            low = data[i + 1] - ord("a")
            out.append((high << 4) | low)

        out_bytes = bytes(out)
        server_logger.debug("NetBIOS Decode output: %r", out_bytes)
        return out_bytes
    except Exception as e:
        server_logger.exception("Error in netbios_decode")
        raise ValueError(f"Error in netbios_decode: {e}")


def netbiosu_encode(data: bytes) -> bytes:
    check_type(data, bytes, "data")

    try:
        server_logger.debug("NetBIOSU Encode input: %r", data)
        out = bytearray()

        for b in data:
            high = (b >> 4) & 0x0F
            low = b & 0x0F
            out.append(ord("A") + high)
            out.append(ord("A") + low)

        out_bytes = bytes(out)
        server_logger.debug("NetBIOSU Encode output: %r", out_bytes)
        return out_bytes
    except Exception as e:
        server_logger.exception("Error in netbiosu_encode")
        raise ValueError(f"Error in netbiosu_encode: {e}")


def netbiosu_decode(data: bytes) -> bytes:
    check_type(data, bytes, "data")

    try:
        server_logger.debug("NetBIOSU Decode input: %r", data)
        if len(data) % 2 != 0:
            raise ValueError("Invalid NetBIOSU data length")

        out = bytearray()

        for i in range(0, len(data), 2):
            high = data[i] - ord("A")
            low = data[i + 1] - ord("A")
            out.append((high << 4) | low)

        out_bytes = bytes(out)
        server_logger.debug("NetBIOSU Decode output: %r", out_bytes)
        return out_bytes
    except Exception as e:
        server_logger.exception("Error in netbiosu_decode")
        raise ValueError(f"Error in netbiosu_decode: {e}")


# Updated malleable_string_to_bytes with try/except as well
_HEX_ESCAPE_RE = re.compile(r"\\x([0-9a-fA-F]{2})")


def malleable_string_to_bytes(value: str) -> bytes:
    """
    Decode valid \\xNN escapes only.
    Leave malformed escapes literal.

    Old approach used `unicode_escape`, which requires perfect `\\xNN` escapes and
    crashes on malformed or partial escapes allowed in malleable C2 profiles.
    New approach decodes only valid `\\xNN` sequences and leaves everything else
    literal, matching Cobalt Strike Mal c2 behavior and never throwing.
    """
    check_type(value, str, "value")

    try:
        out = bytearray()
        i = 0

        while i < len(value):
            if value[i] == "\\" and i + 3 < len(value) and value[i + 1] == "x":
                hex_part = value[i + 2 : i + 4]
                try:
                    out.append(int(hex_part, 16))
                    i += 4
                    continue
                except ValueError:
                    pass  # fall through → literal
            out.append(ord(value[i]))
            i += 1

        return bytes(out)
    except Exception as e:
        server_logger.exception("Error in malleable_string_to_bytes")
        raise ValueError(f"Error in malleable_string_to_bytes: {e}")
