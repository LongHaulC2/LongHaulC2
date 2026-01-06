from mpp import MalleableProfile
from fastapi import Response, FastAPI
from yarl import URL
import logging
from .transform import *

"""
Logic for extracting Malleable C2 options within the profiles. Piggybacks off of MalleableProfile (mpp)
to get the values needed. 

This is currently purely for server side logic, does not have the logic to setup implants with the same options. 
"""
api_logger = logging.getLogger("api")
server_logger = logging.getLogger("server")


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

    def get_allowed_user_agents(self) -> dict: ...
    def get_blocked_user_agents(self) -> dict: ...
    def get_headers_to_add_to_request(self) -> dict:
        """
        Add all the headers specifed by 'header "x-1", "value"' in the malleable c2 profile

        """
        # https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_http-server-config.htm#_Toc65482845
        headers = {}

        # Add in rest of headers based on declared headers
        headers.update(
            {
                stmt.key: stmt.value
                for stmt in self.http_config.data
                if getattr(stmt, "statement", None) == "header"
            }
        )
        server_logger.debug(f"Extracted Headers: {list(headers.items())}")
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
            print(ordered_headers)

        # Reorder the headers according to the desired_order
        ordered_headers = {
            header: headers[header] for header in ordered_headers if header in headers
        }
        print(ordered_headers)
        return ordered_headers
        # You can now return the ordered headers in the response
        # return Response(content="Headers have been reordered.", headers=ordered_headers)

    def get_headers_to_remove_from_request(self) -> dict: ...


class HttpGetBlockServerParser:
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

        """
        headers = {
            stmt.key: stmt.value
            for stmt in self.server.data
            if getattr(stmt, "statement", None) == "header"
        }
        server_logger.debug(f"Extracted Headers: {list(headers.items())}")
        return headers

    def generate_data(self):
        """
        Generates the entire data for the response for the server

        Does all the transforms, data insertion, etc etc and creates body based on that.
        """
        # get task
        task = b"mydata"

        data = self.apply_transforms(task)

        return data

    def get_output_terminator(self):
        """
        Return a tuple: (terminator_type, target_name)
        - terminator_type: "header", "parameter", "print", "uri-append"
        - target_name: header name / parameter key, or None if body
        """
        for stmt in self.server.output.data:
            name = stmt.statement
            value = stmt.value

            if name in ("header", "parameter", "uri-append"):
                return name, value
            elif name == "print":
                return "print", None
            # if multiple terminators, this will return the last one

        # fallback if no terminator found
        return None, None

    def apply_transforms(self, data: bytes) -> bytes:
        """
        Apply output transforms sequentially, in source order.
        """
        # loop over each transform
        for stmt in self.server.output.data:
            name = stmt.statement
            value = stmt.value

            server_logger.debug("Applying transform: %s %r", name, value)

            if name == "prepend":
                data = transform_prepend(data, stmt.value)

            elif name == "append":
                data = transform_append(data, stmt.value)

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

            if name in ("header", "parameter", "uri-append"):
                key = stmt.key
                return name, key
            elif name == "print":
                return "print", None
            # if multiple terminators, this will return the last one

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

            if name in ("header", "parameter", "uri-append"):
                return name, value
            elif name == "print":
                return "print", None
            # if multiple terminators, this will return the last one

        # fallback if no terminator found
        return None, None

    def extract_data(self):
        """
        Does the inverse on the data that is specified in the malleablec2 to make it readable again
        """
        # room for more functions later, and extract_data makes more sense
        # as a function name

        self.apply_transforms()

    def apply_transforms(self, data):
        for stmt in self.client.metadata.data:
            name = stmt.statement
            value = stmt.value

            server_logger.debug("Applying transform: %s %r", name, value)

            if name == "prepend":
                data = undo_transform_prepend(data, stmt.value)

            elif name == "append":
                data = undo_transform_append(data, stmt.value)

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

        """
        headers = {
            stmt.key: stmt.value
            for stmt in self.server.data
            if getattr(stmt, "statement", None) == "header"
        }
        server_logger.debug(f"Extracted Headers: {list(headers.items())}")
        return headers

    def generate_data(self):
        """
        Generates the entire data for the response for the server

        Does all the transforms, data insertion, etc etc and creates body based on that.
        """
        # get task
        task = b"mydata"

        data = self.apply_transforms(task)

        return data

    def get_output_terminator(self):
        """
        Return a tuple: (terminator_type, target_name)
        - terminator_type: "header", "parameter", "print", "uri-append"
        - target_name: header name / parameter key, or None if body
        """
        for stmt in self.server.output.data:
            name = stmt.statement
            value = stmt.value

            if name in ("header", "parameter", "uri-append"):
                return name, value
            elif name == "print":
                return "print", None
            # if multiple terminators, this will return the last one

        # fallback if no terminator found
        return None, None

    def apply_transforms(self, data: bytes) -> bytes:
        """
        Apply output transforms sequentially, in source order.
        """
        # loop over each transform
        for stmt in self.server.output.data:
            name = stmt.statement
            value = stmt.value

            server_logger.debug("Applying transform: %s %r", name, value)

            if name == "prepend":
                data = transform_prepend(data, stmt.value)

            elif name == "append":
                data = transform_append(data, stmt.value)

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

            if name in ("header", "parameter", "uri-append"):
                return name, value
            elif name == "print":
                return "print", None
            # if multiple terminators, this will return the last one

        # fallback if no terminator found
        return None, None

    def extract_data(self):
        """
        Does the inverse on the data that is specified in the malleablec2 to make it readable again
        """
        # room for more functions later, and extract_data makes more sense
        # as a function name

        self.apply_transforms()

    def apply_transforms(self, data):
        for stmt in self.client.output.data:
            name = stmt.statement
            value = stmt.value

            server_logger.debug("Applying transform: %s %r", name, value)

            if name == "prepend":
                data = undo_transform_prepend(data, stmt.value)

            elif name == "append":
                data = undo_transform_append(data, stmt.value)

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


# other parsers here too...
###################################
# HTTPS Parse
###################################

###################################
# ICMP Parse [custom addon, parser still works on them]
###################################
