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
class HttpServerEmitter:
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

    def get_terminator(self):
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


class HttpClientEmitter:
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


# other parsers here too...
###################################
# HTTPS Parse
###################################

###################################
# ICMP Parse [custom addon, parser still works on them]
###################################
