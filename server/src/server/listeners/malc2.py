from mpp import MalleableProfile
from fastapi import Response, FastAPI
from yarl import URL

"""
Logic for extracting Malleable C2 options within the profiles. Piggybacks off of MalleableProfile (mpp)
to get the values needed. 

This is currently purely for server side logic, does not have the logic to setup implants with the same options. 
"""


###################################
# HTTP Parse
###################################
class HttpServerEmitter:
    def __init__(self, server_block):
        self.server = server_block

    def headers(self) -> dict:
        return {
            stmt.key: stmt.value
            for stmt in self.server.data
            if getattr(stmt, "statement", None) == "header"
        }

    # just a placeholer for append. Maybe have a func that puts the body togheter
    # ex, parses all the things, adds in payload, then returns body
    def output_bytes(self) -> bytes:
        output = self.server.output.data

        return b"".join(
            (s.value if isinstance(s.value, bytes) else s.value.encode("latin-1"))
            for s in reversed(output)
            if s.statement == "prepend"
        )

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
