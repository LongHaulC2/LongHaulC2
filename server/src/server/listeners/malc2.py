import re
import tempfile

import structlog
from mpp import MalleableProfile

from ..utils.checks import check_type
from .transform import (
    base64_decode,
    base64_encode,
    base64url_decode,
    base64url_encode,
    netbios_decode,
    netbios_encode,
    netbiosu_decode,
    netbiosu_encode,
    transform_append,
    transform_prepend,
    undo_transform_append,
    undo_transform_prepend,
    xor_mask,
)

"""
Logic for extracting Malleable C2 options within the profiles. Piggybacks off of MalleableProfile (mpp)
to get the values needed.

This is currently purely for server side logic, does not have the logic to setup implants with the same options.
"""
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")

###################################
# Profile Cleaning/Util funcs
###################################


def load_malleable_profile(malleable_c2_profile: str) -> MalleableProfile:
    """
    Helper to safely load the MalleableProfile.
    Handles the quirk where mpp requires a file path rather than a string.

    Additionally, formats/cleans various quirks with Malleable profiles, ex, delimiters.

    """
    server_logger.debug("Parsing Malleable C2 profile.")

    try:
        # with open(path, "r") as file:
        #     content = file.read()

        # Create a temporary file because mpp library requires a file path
        with tempfile.NamedTemporaryFile("w+", suffix=".profile") as tmp_file:
            tmp_file.write(malleable_c2_profile)
            tmp_file.flush()
            mp = MalleableProfile(profile=tmp_file.name)

            # clean up delims
            clean_ast_backslash_delimiters(mp.profile)

            return mp

    except Exception as e:
        server_logger.error("Failed to parse Malleable Profile", error=str(e))
        raise e


"""
TLDR: MPP dosen't delim strings, so profile values such as:

`"<!DOCTYPE html><html lang=\"en\" xml:lang=\"en\" xmlns=\"http://www.w3.org/1999/xhtml\"`

show up with literal \" in the cPP jinja build. These functions below clean it up so they don't have this,
and instead turn out like:

`<!DOCTYPE html><html lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml`

"""


def _clean_string(s):
    """
    Removes specific delimiter artifacts from a string.
    Adjust the replace logic below if you strictly want to delete them
    instead of unescaping them.
    """
    if isinstance(s, str):
        # This unescapes \" to ", which is usually the intent for C2 profiles.
        # If you strictly want to DELETE the characters, change '"' to ''
        return s.replace('\\"', '"').replace('"\\', '"')
    return s


def clean_ast_backslash_delimiters(node):
    """
    Recursively traverses the AST and cleans 'value' and 'key' fields.
    """
    return  # temp disable
    # Handle Dictionary (recurse into values)
    if isinstance(node, dict):
        for _key, value in node.values():
            clean_ast_backslash_delimiters(value)

    # Handle List (recurse into items)
    elif isinstance(node, list):
        for item in node:
            clean_ast_backslash_delimiters(item)

    # Handle 'Block' objects (recurse into the 'data' attribute)
    elif hasattr(node, "data") and isinstance(node.data, list):
        clean_ast_backslash_delimiters(node.data)

    # Handle 'Option' and 'Statement' objects (clean the 'value' and 'key')
    # We check for 'value' attribute which both Option and Statement have.
    elif hasattr(node, "value"):
        # Clean the value
        node.value = _clean_string(node.value)

        # Statements also have a 'key' attribute (e.g., header name)
        if hasattr(node, "key") and node.key:
            node.key = _clean_string(node.key)


def unescape_malleable_bytes(data: bytes) -> bytes:
    R"""
    Parses a bytestring and replaces Malleable C2 escape sequences
    (\n, \r, \t, \x##, \u####, \\) with their actual byte values.
    """
    # check_type(data, bytes, "data")
    if isinstance(data, str):
        # 'latin-1' is safest for C2 because it maps 1-to-1 to bytes without crashing on weird chars
        data = data.encode("latin-1")

    def replace_match(match):
        seq = match.group(0)

        # Handle Standard Escapes
        if seq == b"\\n":
            return b"\n"
        if seq == b"\\r":
            return b"\r"
        if seq == b"\\t":
            return b"\t"
        if seq == b'\\"':
            return b'"'
        if seq == b"\\\\":
            return b"\\"

        # Handle Hex Bytes (\x41 -> A)
        if seq.startswith(b"\\x"):
            # Convert b'41' -> int 65 -> byte b'A'
            return bytes([int(seq[2:], 16)])  # noqa - RUFF says use base, leave it, otherwise it'll break

        # Handle Unicode (\u1234 -> UTF-8 bytes)
        if seq.startswith(b"\\u"):
            # Convert hex -> int -> char -> utf-8 encoded bytes
            char_code = int(seq[2:], 16)  # noqa - RUFF says use base, leave it, otherwise it'll break
            return chr(char_code).encode("utf-8")

        return seq

    # Regex breakdown:
    # \\x[0-9a-fA-F]{2}  -> Matches \x##
    # \\u[0-9a-fA-F]{4}  -> Matches \u####
    # \\[nrt"\\]         -> Matches \n, \r, \t, \", \\
    pattern = re.compile(b'\\\\(?:x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|[nrt"\\\\])')

    return pattern.sub(replace_match, data)


###################################
# HTTP Parse
###################################
class HttpConfigBlockServerParser:
    """ """

    def __init__(self, http_config):
        """
        Server block: Parsed server block. Ex: mp.http_post.server

        Handles the server parsing
        """
        self.http_config = http_config

    def get_allowed_user_agents(self) -> list:
        # Iterate over the objects inside the http_config
        for stmt in self.http_config.data:
            # Check if the object has an 'option' attribute and matches 'block_useragents'
            if hasattr(stmt, "option") and stmt.option == "allow_useragents":
                return stmt.value.strip().split(",")
        return []

    def get_blocked_user_agents(self) -> list:
        for stmt in self.http_config.data:
            # Check if the object has an 'option' attribute and matches 'block_useragents'
            if hasattr(stmt, "option") and stmt.option == "block_useragents":
                return stmt.value.strip().split(",")
        return []

    def get_headers_to_add_to_request(self) -> dict:
        """
        Add all the headers specifed by 'header "x-1", "value"' in the malleable c2 profile

        """
        # https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_http-server-config.htm#_Toc65482845
        headers = {}

        # Add in rest of headers based on declared headers
        headers.update(
            {stmt.key: stmt.value for stmt in self.http_config.data if getattr(stmt, "statement", None) == "header"}
        )
        server_logger.debug("Extracted Headers", headers=list(headers.items()))
        return headers

    def reorder_headers(self, headers) -> dict:
        """
        IF, and a big IF the headers are included in the current headers,
        re-order them according to the malleable c2 profile set headers.

        If a header is NOT ALREADY included in the header list, it WILL NOT be added.

        returns new headers.

        https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_http-server-config.htm#_Toc65482845

        """
        # Sample headers (this would be the actual headers in a real request/response)
        # headers = {
        #     "X-Header-1": "Value 1",
        #     "X-Header-2": "Value 2",
        #     "X-Header-3": "Value 3",
        #     "X-Header-4": "Value 4",
        # }

        # # Define the order you want the headers to follow (you can define custom order)
        # desired_order = ["X-Header-3", "X-Header-1", "X-Header-2", "X-Header-4"]

        ordered_headers = self.http_config.headers.value
        if ordered_headers:
            # cleanup  headers, turn into a list
            ordered_headers = ordered_headers.strip().split(",")

            # Strip whitespace around each individual header
            ordered_headers = [header.strip() for header in ordered_headers]
            # print(ordered_headers)

        # Reorder the headers according to the desired_order
        return {header: headers[header] for header in ordered_headers if header in headers}
        # print(ordered_headers)
        # You can now return the ordered headers in the response
        # return Response(content="Headers have been reordered.", headers=ordered_headers)

    def get_headers_to_remove_from_request(self) -> dict:
        ...


class HttpGetBlockServerParser:
    def __init__(self, server_block):
        """
        Server block: Parsed server block. Ex: mp.http_post.server

        Handles the server parsing
        """
        self.server = server_block

    def headers(self) -> dict:
        """
        Extracts headers from malc2 profile server block

        Returns a dict of headers:
        {
            "Myheader1":"SomeValue"
        }

        Ex:
        server {
            # *no* params in server block, doesn't make sense. That is specified by client
            # headers only
            header "Content-Type" "image/gif";
            header "http_post->server->header" "image/gif";

            output {
                print;
            }
        }

        """
        headers = {stmt.key: stmt.value for stmt in self.server.data if getattr(stmt, "statement", None) == "header"}
        server_logger.debug("Extracted Headers", header=list(headers.items()))
        return headers

    def generate_data(self, data: bytes):
        """
        Generates the entire data for the response for the server

        Does all the transforms, data insertion, etc etc and creates body based on that.
        """
        check_type(data, bytes, "data")
        block_field = self.server.output
        return self.apply_transforms(data, block_field=block_field)

    def get_output_terminator(self):
        """
        Return a tuple: (terminator_type, target_name)
        - terminator_type: "header", "parameter", "print", "uri-append"
        - target_name: header name / parameter key, or None if body
        """
        for stmt in self.server.output.data:
            name = stmt.statement
            value = stmt.value

            # if name in ("header", "parameter", "uri-append"):
            #     return name, value
            # elif name == "print":
            #     return "print", None
            # if multiple terminators, this will return the last one

            if name == "uri-append":
                return name, value
            if name in ("parameter", "header"):
                return name, stmt.key
            if name == "print":
                return "print", None

        # fallback if no terminator found
        return None, None

    def apply_transforms(self, data: bytes, block_field) -> bytes:
        """
        Apply output transforms sequentially, in source order.
        """
        check_type(data, bytes, "data")

        # loop over each transform
        for stmt in block_field.data:  # self.server.output.data:
            name = stmt.statement
            value = unescape_malleable_bytes(stmt.value)

            server_logger.debug("Applying transform: %s %r", name, value)

            if name == "prepend":
                data = transform_prepend(data, value)

            elif name == "append":
                data = transform_append(data, value)

            elif name == "base64":
                data = base64_encode(data)

            elif name == "base64url":
                data = base64url_encode(data)

            elif name == "netbios":
                data = netbios_encode(data)

            elif name == "netbiosu":
                data = netbiosu_encode(data)

            elif name == "mask":
                # assuming stmt.key or stmt.value holds the mask key
                data = xor_mask(data, value)

            else:
                server_logger.debug("Skipping unsupported transform: %s", name)

            server_logger.debug("Data after %s: %r", name, data)

        return data

    def get_server_output_transforms_list(self):
        """
        Get a list of the transforms (ex, prepend, base64, etc)

        """
        output = self.server.output
        return output.data[:-1] if output and output.data else []

    def get_headers_and_parameters_list(self) -> list:
        """
        Gets the headers and parameters outside of the metadata block in the client.

        Returns a list of dicts: [{'name': 'parameter', 'key':'utmac', 'value':'1234'},...]

        Ex:
        server {
            # these
            header "Content-Type" "image/gif";

            output {
                print;
            }
        }

        https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_profile-language.htm#_Toc65482837
        """

        # note, using a list of dicts. I was going to use a dict originally,
        # but it turn sout HTTP can have multiple params/headers of the same name,
        # ex, url/a?=b?a=c,  etc. Dict only has one key per param, list  of dicts can
        # have as many as specified.
        headers_and_parameters_list = []

        for stmt in self.server.data:
            name = stmt.statement
            value = stmt.value
            key = stmt.key

            if name in ("parameter", "header"):
                data = {"name": name, "key": key, "value": value}
                headers_and_parameters_list.append(data)

            else:
                continue

        return headers_and_parameters_list


"""
    # client -> serer
	client {
        # can ignore all of these on the server side
		parameter "utmac" "UA-2202604-2";
		parameter "utmcn" "1";
		parameter "utmcs" "ISO-8859-1";
		parameter "utmsr" "1280x1024";
		parameter "utmsc" "32-bit";
		parameter "utmul" "en-US";

        # this is waht we need
		metadata {
			base64url;
			prepend "__utma";
			parameter "utmcc";
		}
	}

"""


class HttpGetBlockClientParser:
    """
    Handles all the client parsing
    """

    def __init__(self, client_block):
        """
        Server block: Parsed server block. Ex: mp.http_post.server

        Handles the server parsing
        """
        self.client = client_block

    def get_metadata_terminator(self):
        """
        Return a tuple: (terminator_type, target_name)
        - terminator_type: "header", "parameter", "print", "uri-append"
        - target_name: header name / parameter key, or None if body
        """
        for stmt in self.client.metadata.data:
            name = stmt.statement
            value = stmt.value

            # if name in ("header", "parameter", "uri-append"):
            #     key = stmt.key
            #     return name, key
            # elif name == "print":
            #     return "print", None
            # if multiple terminators, this will return the last one

            if name == "uri-append":
                return name, value
            if name in ("parameter", "header"):
                return name, stmt.key
            if name == "print":
                return "print", None

        # fallback if no terminator found
        return None, None

    def get_output_terminator(self):
        """
        Return a tuple: (terminator_type, target_name)
        - terminator_type: "header", "parameter", "print", "uri-append"
        - target_name: header name / parameter key, or None if body
        """
        for stmt in self.client.output.data:
            name = stmt.statement
            value = stmt.value

            # if name in ("header", "parameter", "uri-append"):
            #     return name, value
            # elif name == "print":
            #     return "print", None
            # if multiple terminators, this will return the last one

            if name == "uri-append":
                return name, value
            if name in ("parameter", "header"):
                return name, stmt.key
            if name == "print":
                return "print", None

        # fallback if no terminator found
        return None, None

    def apply_transforms(self, data: bytes, block_field):
        """
        Applies transforms to data coming in from implant.

        Because it is inbound, the transforms are reversed, aka applied last to first,
        as the implant has created them first to last.
        """

        check_type(data, bytes, "data")

        for stmt in reversed(block_field.data):  # Reversed, see docstring
            name = stmt.statement
            value = unescape_malleable_bytes(stmt.value)

            server_logger.debug("Applying transform: %s %r", name, value)

            if name == "prepend":
                data = undo_transform_prepend(data, value)

            elif name == "append":
                data = undo_transform_append(data, value)

            elif name == "base64":
                data = base64_decode(data)

            elif name == "base64url":
                data = base64url_decode(data)

            elif name == "netbios":
                data = netbios_decode(data)

            elif name == "netbiosu":
                data = netbiosu_decode(data)

            elif name == "mask":
                # assuming stmt.key or stmt.value holds the mask key
                data = xor_mask(data, value)

            else:
                server_logger.debug("Skipping unsupported transform: %s", name)

            server_logger.debug("Data after %s: %r", name, data)

        return data

    # def get_client_output_transforms_list(self):
    #     """
    #     Get a list of the transforms (ex, prepend, base64, etc)

    #     """
    #     output = self.client.client.output
    #     return output.data[:-1] if output and output.data else []

    def get_client_metadata_transforms_list(self):
        """
        Get a list of the transforms (ex, prepend, base64, etc)

        """
        # problllem, some keys have value some dont. probnably need addl logic for
        # if value, put in
        output = self.client.metadata
        return output.data[:-1] if output and output.data else []

    def get_headers_and_parameters_list(self) -> list:
        """
        Gets the headers and parameters outside of the metadata block in the client.

        Returns a list of dicts: [{'name': 'parameter', 'key':'utmac', 'value':'1234'},...]

        Ex:
        client {
            # these
            parameter "utmac" "UA-2202604-2";
            parameter "utmcn" "1";
            parameter "utmcs" "ISO-8859-1";
            parameter "utmsr" "1280x1024";
            parameter "utmsc" "32-bit";
            parameter "utmul" "en-US";

            # not this
            metadata {
                base64url;
                header "utmcc";
            }
        }


        https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_profile-language.htm#_Toc65482837
        """

        # note, using a list of dicts. I was going to use a dict originally,
        # but it turn sout HTTP can have multiple params/headers of the same name,
        # ex, url/a?=b?a=c,  etc. Dict only has one key per param, list  of dicts can
        # have as many as specified.
        headers_and_parameters_list = []

        for stmt in self.client.data:
            name = stmt.statement
            value = stmt.value
            key = stmt.key

            if name in ("parameter", "header"):
                data = {"name": name, "key": key, "value": value}
                headers_and_parameters_list.append(data)

            else:
                continue

        return headers_and_parameters_list


# post block has a few differneces,so this accounts for that
# - no metadata field, only ID, and OUTPUT
class HttpPostBlockServerParser:
    def __init__(self, server_block):
        """
        Server block: Parsed server block. Ex: mp.http_post.server

        Handles the server parsing
        """
        self.server = server_block

    def headers(self) -> dict:
        """
        Extracts headers from malc2 profile

        Returns a dict of headers:
        {
            "Myheader1":"SomeValue"
        }

        Ex:
        server {
            # *no* params in server block, doesn't make sense. That is specified by client
            # headers only
            header "Content-Type" "image/gif";
            header "http_post->server->header" "image/gif";

            output {
                print;
            }
        }
        """
        headers = {stmt.key: stmt.value for stmt in self.server.data if getattr(stmt, "statement", None) == "header"}
        server_logger.debug("Extracted Headers", headers=list(headers.items()))
        return headers

    def get_output_terminator(self):
        """
        Return a tuple: (terminator_type, target_name)
        - terminator_type: "header", "parameter", "print", "uri-append"
        - target_name: header name / parameter key, or None if body
        """
        for stmt in self.server.output.data:
            name = stmt.statement
            value = stmt.value

            # if name in ("header", "parameter", "uri-append"):
            #     return name, value
            # elif name == "print":
            #     return "print", None
            # if multiple terminators, this will return the last one

            if name == "uri-append":
                return name, value
            if name in ("parameter", "header"):
                return name, stmt.key
            if name == "print":
                return "print", None

        # fallback if no terminator found
        return None, None

    def apply_transforms(self, data: bytes, block_field) -> bytes:
        """
        Apply output transforms sequentially, in source order.
        """
        check_type(data, bytes, "data")

        # loop over each transform
        for stmt in block_field.data:  # self.server.output.data:
            name = stmt.statement
            value = unescape_malleable_bytes(stmt.value)

            server_logger.debug("Applying transform: %s %r", name, value)

            if name == "prepend":
                data = transform_prepend(data, value)

            elif name == "append":
                data = transform_append(data, value)

            elif name == "base64":
                data = base64_encode(data)

            elif name == "base64url":
                data = base64url_encode(data)

            elif name == "netbios":
                data = netbios_encode(data)

            elif name == "netbiosu":
                data = netbiosu_encode(data)

            elif name == "mask":
                # assuming stmt.key or stmt.value holds the mask key
                data = xor_mask(data, value)

            else:
                server_logger.debug("Skipping unsupported transform: %s", name)

            server_logger.debug("Data after %s: %r", name, data)

        return data

    def get_headers_and_parameters_list(self) -> list:
        """
        Gets the headers and parameters outside of the metadata block in the client.

        Returns a list of dicts: [{'name': 'parameter', 'key':'utmac', 'value':'1234'},...]

        Ex:
        server {
            # these
            header "Content-Type" "image/gif";

            output {
                print;
            }
        }

        https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_profile-language.htm#_Toc65482837
        """

        # note, using a list of dicts. I was going to use a dict originally,
        # but it turn sout HTTP can have multiple params/headers of the same name,
        # ex, url/a?=b?a=c,  etc. Dict only has one key per param, list  of dicts can
        # have as many as specified.
        headers_and_parameters_list = []

        for stmt in self.server.data:
            name = stmt.statement
            value = stmt.value
            key = stmt.key

            if name in ("parameter", "header"):
                data = {"name": name, "key": key, "value": value}
                headers_and_parameters_list.append(data)

            else:
                continue

        return headers_and_parameters_list


class HttpPostBlockClientParser:
    """
    Handles all the client parsing
    """

    def __init__(self, client_block):
        """
        Server block: Parsed server block. Ex: mp.http_post.server

        Handles the server parsing
        """
        self.client = client_block

    def get_output_terminator(self):
        """
        Return a tuple: (terminator_type, target_name)
        - terminator_type: "header", "parameter", "print", "uri-append"
        - target_name: header name / parameter key, or None if body
        """
        for stmt in self.client.output.data:
            name = stmt.statement
            value = stmt.value

            if name == "uri-append":
                return name, value
            if name in ("parameter", "header"):
                return name, stmt.key
            if name == "print":
                return "print", None
            # if multiple terminators, this will return the last one

        # fallback if no terminator found
        return None, None

    def get_id_terminator(self):
        """
        Return a tuple: (terminator_type, target_name)
        - terminator_type: "header", "parameter", "print", "uri-append"
        - target_name: header name / parameter key, or None if body
        """
        for stmt in self.client.id.data:
            name = stmt.statement
            value = stmt.value

            # print(self.client.id.data)

            # header and parameter are in  KEY wtf
            # [Statement(statement=base64url, value=""), Statement(statement=header, key="utmcc", value="")]
            # [Statement(statement=parameter, key="utmac", value="")]

            if name == "uri-append":
                return name, value
            if name in ("parameter", "header"):
                return name, stmt.key
            if name == "print":
                return "print", None
            # if multiple terminators, this will return the last one

        # fallback if no terminator found
        return None, None

    def apply_transforms(self, data, block_field):
        """
        Applies transforms to data coming in from implant.

        Because it is inbound, the transforms are reversed, aka applied last to first,
        as the implant has created them first to last.
        """
        check_type(data, bytes, "data")

        for stmt in reversed(block_field.data):  # self.client.output.data:
            name = stmt.statement
            value = unescape_malleable_bytes(stmt.value)

            server_logger.debug("Applying transform: %s %r", name, value)

            if name == "prepend":
                data = undo_transform_prepend(data, value)

            elif name == "append":
                data = undo_transform_append(data, value)

            elif name == "base64":
                data = base64_decode(data)

            elif name == "base64url":
                data = base64url_decode(data)

            elif name == "netbios":
                data = netbios_decode(data)

            elif name == "netbiosu":
                data = netbiosu_decode(data)

            elif name == "mask":
                # assuming stmt.key or stmt.value holds the mask key
                data = xor_mask(data, value)

            else:
                server_logger.debug("Skipping unsupported transform: %s", name)

            server_logger.debug("Data after %s: %r", name, data)

        return data

    def post_client_id_transforms_list(self):
        """
        Get a list of the transforms (ex, prepend, base64, etc)

        """
        output = self.client.id
        return output.data[:-1] if output and output.data else []

    def post_client_output_transforms_list(self):
        """
        Get a list of the transforms (ex, prepend, base64, etc)

        """
        output = self.client.output
        return output.data[:-1] if output and output.data else []

    def get_headers_and_parameters_list(self) -> list:
        """
        Gets the headers and parameters outside of the metadata block in the client.

        Returns a list of dicts: [{'name': 'parameter', 'key':'utmac', 'value':'1234'},...]

        Ex:
        client {
            id {
                base64url;
                parameter "utmac";
            }

            # these
            parameter "utmcn" "1";
            parameter "utmcs" "ISO-8859-1";
            parameter "utmsr" "1280x1024";
            parameter "utmsc" "32-bit";
            parameter "utmul" "en-US";

            output {
                base64url;
                header "utmcc";
            }
        }


        https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_profile-language.htm#_Toc65482837
        """

        # note, using a list of dicts. I was going to use a dict originally,
        # but it turn sout HTTP can have multiple params/headers of the same name,
        # ex, url/a?=b?a=c,  etc. Dict only has one key per param, list  of dicts can
        # have as many as specified.
        headers_and_parameters_list = []

        for stmt in self.client.data:
            name = stmt.statement
            value = stmt.value
            key = stmt.key

            if name in ("parameter", "header"):
                data = {"name": name, "key": key, "value": value}
                headers_and_parameters_list.append(data)

            else:
                continue

        return headers_and_parameters_list


# other parsers here too...
###################################
# HTTPS Parse
###################################

###################################
# ICMP Parse [custom addon, parser still works on them]
###################################
