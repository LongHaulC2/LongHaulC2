from mpp import MalleableProfile
from fastapi import Response, FastAPI
from yarl import URL
import logging

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
        # body

        # Get prepend and append data
        prepend_data: bytes = self.get_prepend()
        append_data: bytes = self.get_append()
        # get next task
        task = b"sometask"
        # Do transformations

        # stick it all together

        body = b"".join([prepend_data, task, append_data])

        return body

    # just a placeholer for append. Maybe have a func that puts the body togheter
    # ex, parses all the things, adds in payload, then returns body
    def get_prepend(self) -> bytes:
        """
        Get prepend data for the server response, from the Malleable C2 profile

        Note: Prepend is weird, and takes the data in reverse order:
            prepend "\x01";
            prepend "\x02";
            prepend "\x03";

        This will return the data as : "\x03, \x02, \x01" (or: `\x03\x02\x01` on the wire),
        as it is "prepending" to each current data blob

        Don't worry, this function handles it properly, and will do the conversion for you to the correct
        `\x03\x02\x01`

        Returns bytes.
        """
        output = self.server.output.data

        prepend_data = b"".join(
            (s.value if isinstance(s.value, bytes) else s.value.encode("latin-1"))
            for s in reversed(output)
            if s.statement == "prepend"
        )
        server_logger.debug(f"Extracted prepend data: {prepend_data.hex()}")

        return prepend_data

    def get_append(self) -> bytes:
        """
        Get append data for the server response, from the Malleable C2 profile

        Returns bytes.
        """
        output = self.server.output.data

        append_data = b"".join(
            (s.value if isinstance(s.value, bytes) else s.value.encode("latin-1"))
            for s in output
            if s.statement == "append"
        )
        server_logger.debug(f"Extracted append data: {append_data.hex()}")

        return append_data

    def response_body(self):
        ...
        data = ...
        # parse:
        # prepend, append, etc etc into a valid body
        # reutnr body


# other parsers here too...
###################################
# HTTPS Parse
###################################

###################################
# ICMP Parse [custom addon, parser still works on them]
###################################
