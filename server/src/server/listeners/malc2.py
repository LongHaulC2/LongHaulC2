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

    def generate_body(self):
        """
        Generates the entire body for the response for the server

        Does all the transforms, data insertion, etc etc and creates body based on that.
        """
        # get task
        task = b"mydata"

        body = self.apply_transforms(task)

        return body

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


# other parsers here too...
###################################
# HTTPS Parse
###################################

###################################
# ICMP Parse [custom addon, parser still works on them]
###################################
