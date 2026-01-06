# PLACEHOLDER while I figure out the supervisor logic

# must haves: run entrypoint, that is a func, most flexible + no class init then by the supervisor (adds complexity)

from time import sleep
from edwh_uuid7 import uuid7

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
    register_http_get_route(method=http_get_method, uri=URL(mp.http_get.uri.value))

    # setup post route
    http_post_method = getattr(mp.http_post.verb, "value", "POST")
    register_http_post_route(method=http_post_method, uri=URL(mp.http_post.uri.value))

    # reload needs to be OFF.
    # server_header=false disabled  "server uvicorn" in the response
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, server_header=False)


###################################
# Various Handlers
###################################


def check_if_data(data_from_request):  #
    """
    Check if the request had data (evaluates falsey-ness). If not, return a 400.

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
    Checks user agent. If allowed (via profile), returns true
    else, false
    """
    ...
    return True
    if user_agent != "bob":
        return False
    else:
        return True
    # if user agent matches block, return a 400? or just sinkhole
    # if user agent matches allow, return


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


async def http_get(request: Request):
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

    # 204 on fail. Can't sinkhole without extra setup/steps atm.
    if not check_user_agent(user_agent):
        return Response(status_code=204)

    """
    Handle inputted data form fastapi

    """
    # all_params = dict(request.query_params)
    # print(all_params)

    # steps
    # 1. get last item in metadata
    # terminator_type = "parameter"

    # 2. Switch case based on terminator type

    # 3. extract data based on term, then de-obsfucate as needed

    hce = HttpGetBlockClientParser(client_block=mp.http_get.client)
    # extract terminator data
    terminator_type, terminator_key = hce.get_metadata_terminator()

    # print(terminator_type)
    # print(terminator_key)

    match terminator_type:
        # [X] works
        case "header":
            # bug, header capatalziation. They should be case insensitive. Lowering for
            # the comparison here, they previsouly were not, causing a mismatch.
            normalized_headers = {k.lower(): v for k, v in request.headers.items()}
            data_from_request = normalized_headers.get(terminator_key.lower(), None)

            check_if_data(data_from_request)

            print(request.headers)
            print(f"Data from request: {data_from_request}")

            try:
                hce = HttpGetBlockClientParser(client_block=mp.http_get.client)
                print(
                    f"De-Obsfucated data: {hce.apply_transforms(data=data_from_request)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail="Invalid or malformed client data"
                )

        # [X] works
        case "parameter":
            data_from_request = request.query_params.get(terminator_key, None)
            print(f"Data from request: {data_from_request}")

            check_if_data(data_from_request)

            try:
                hce = HttpGetBlockClientParser(client_block=mp.http_get.client)
                print(
                    f"De-Obsfucated data: {hce.apply_transforms(data=data_from_request)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail="Invalid or malformed client data"
                )

        # [X] works
        case "print":
            # in body, so just get body
            data_from_request = await request.body()

            check_if_data(data_from_request)

            try:
                hce = HttpGetBlockClientParser(client_block=mp.http_get.client)
                print(
                    f"De-Obsfucated data: {hce.apply_transforms(data=data_from_request)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail="Invalid or malformed client data"
                )

        case _:
            # unknown terminator
            print("Unknown terminator: %r", terminator_type)
            # throw error cuz we can't continue if we don't have the task

    """
    Setup a response for the implant

    """
    # pass in block to respective class
    emitter = HttpGetBlockServerParser(mp.http_get.server)

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
    uri-append 	        Append to URI (seperate function, see http_get_uri)
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


async def http_get_uri(request: Request, data: str):
    """ """
    print(request)
    print(data)

    # we can assume URI terminator is uri-append.
    # data is the /someendpoint/<HERE>, so we just need to transform it.

    full_uri = str(
        request.url
    )  # Full URL including the scheme, host, path, and query params. useful for logging

    try:
        hce = HttpGetBlockClientParser(client_block=mp.http_get.client)
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
    emitter = HttpGetBlockServerParser(mp.http_get.server)

    # get the stuff we need from it
    headers = emitter.headers()
    data = emitter.generate_data()

    # note, payload would need to be inserted somehwere here too.  Ex,
    # redis lookup for next task -> insert where print it

    # based on terminationstatement, need to store data in certain location
    # Ex: header: store in header
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

        case None:
            # fallback if no terminator\

            body = data
            return Response(content=body, headers=headers)

        case _:
            # unknown terminator
            print("Unknown terminator: %r", terminator_type)
            body = data
            return Response(status_code=500)


def register_http_get_route(
    uri: URL,
    method: str,
):
    """
    Registeres routes. Prevents these being called on import as well.
    """
    app.add_api_route(
        path=str(URL(uri)),
        endpoint=http_get,  # logic for endpoint here
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
        endpoint=http_get_uri,  # The handler function for this route
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


###################################
# HTTP POST
###################################
"""
HTTP POST with CS is where task response data is sent back to

"""


async def http_post(request: Request):
    """
    HTTP POST endpoint for the HTTP listener.

    Note:
    - Accepts all URL parameters via **kwargs.
    - OpenAPI parameter documentation is not generated due to the **kwargs
    - This design enables a more flexible and malleable C2 interface.

    """

    """
    Handle inputted data form fastapi

    """
    # all_params = dict(request.query_params)
    # print(all_params)

    # steps
    # 1. get last item in metadata
    # terminator_type = "parameter"

    # 2. Switch case based on terminator type

    # 3. extract data based on term, then de-obsfucate as needed

    hce = HttpPostBlockClientParser(client_block=mp.http_post.client)
    # extract terminator data
    # for some reason, http-post uses output, not metadata
    terminator_type, terminator_key = hce.get_output_terminator()

    # print(terminator_type)
    # print(terminator_key)

    match terminator_type:
        # [X] works
        case "header":
            normalized_headers = {k.lower(): v for k, v in request.headers.items()}
            data_from_request = normalized_headers.get(terminator_key.lower())
            print(f"Data from request: {data_from_request}")

            check_if_data(data_from_request)

            try:
                hce = HttpPostBlockClientParser(client_block=mp.http_post.client)
                print(
                    f"De-Obsfucated data: {hce.apply_transforms(data=data_from_request)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail="Invalid or malformed client data"
                )
        # [X] works
        case "parameter":
            data_from_request = request.query_params.get(terminator_key)
            print(f"Data from request: {data_from_request}")

            check_if_data(data_from_request)

            try:
                hce = HttpPostBlockClientParser(client_block=mp.http_post.client)
                print(
                    f"De-Obsfucated data: {hce.apply_transforms(data=data_from_request)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail="Invalid or malformed client data"
                )
        # [X] works
        case "print":
            # in body, so just get body
            data_from_request = await request.body()

            check_if_data(data_from_request)

            try:
                hce = HttpPostBlockClientParser(client_block=mp.http_post.client)
                print(
                    f"De-Obsfucated data: {hce.apply_transforms(data=data_from_request)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail="Invalid or malformed client data"
                )
        case _:
            # unknown terminator
            print("Unknown terminator: %r", terminator_type)
            # throw error cuz we can't continue if we don't have the task

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


async def http_post_uri(request: Request, data: str):
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


def register_http_post_route(
    uri: URL,
    method: str,
):
    """
    Registeres routes. Prevents these being called on import as well.
    """
    # HTTP POST ROUTE
    app.add_api_route(
        path=str(URL(uri)),
        endpoint=http_post,  # logic for endpoint here
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
        endpoint=http_post_uri,  # The handler function for this route
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
