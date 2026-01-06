# PLACEHOLDER while I figure out the supervisor logic

# must haves: run entrypoint, that is a func, most flexible + no class init then by the supervisor (adds complexity)

from time import sleep
from edwh_uuid7 import uuid7

from mpp import MalleableProfile
from fastapi import Response, FastAPI, Request
from fastapi.responses import JSONResponse
from yarl import URL
import uvicorn

from ..malc2 import HttpServerEmitter, HttpClientEmitter

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

    # setup get route
    http_get_method = getattr(mp.http_get.verb, "value", "GET")
    register_http_get_route(method=http_get_method, uri=URL(mp.http_get.uri.value))

    # setup post route
    http_post_method = getattr(mp.http_post.verb, "value", "POST")
    register_http_post_route(method=http_post_method, uri=URL(mp.http_post.uri.value))

    # reload needs to be OFF.
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


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

    hce = HttpClientEmitter(client_block=mp.http_get.client)
    # extract terminator data
    terminator_type, terminator_key = hce.get_metadata_terminator()

    # print(terminator_type)
    # print(terminator_key)

    match terminator_type:
        case "header":
            # in header, get whichheader from malprof, and pull out
            print("HEADER")
            ...

        case "parameter":
            # get URLparameter
            # ex, would  get value ofutmcc
            data_from_request = request.query_params.get(terminator_key)
            print(f"Data from request: {data_from_request}")

            print("parameter")
            hce = HttpClientEmitter(client_block=mp.http_get.client)
            print(f"De-Obsfucated data: {hce.apply_transforms(data=data_from_request)}")

            ...

        case "uri-append":
            # assuming its something like /adskjfksdfjsdlkfjasdklfsjdaklfsd==
            print("uri_append")

            ...

        case "print":
            # in body, so just get body
            print("print")
            ...

        case None:
            ...

        case _:
            # unknown terminator
            print("Unknown terminator: %r", terminator_type)

    """
    Setup a response for the implant

    """

    # pass in block to respective class
    emitter = HttpServerEmitter(mp.http_get.server)

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
    uri-append 	        Append to URI
    """
    terminator_type, target = emitter.get_terminator()

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


###################################
# HTTP POST
###################################
"""
HTTP POST with CS is where task response data is sent back to

"""


async def http_post():
    emitter = HttpServerEmitter(mp.http_post.server)

    headers = emitter.headers()
    body = emitter.output_bytes()

    # note, payload would need to be inserted into redis:
    # ex, strip all BS, connect to redis, dump into it.

    return Response(content=body, headers=headers)


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
        endpoint=http_get,  # logic for endpoint here
        methods=[method],
        # response_model=dict,
        # tags=["items"],
    )
