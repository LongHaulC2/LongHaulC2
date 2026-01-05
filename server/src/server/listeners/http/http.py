# PLACEHOLDER while I figure out the supervisor logic

# must haves: run entrypoint, that is a func, most flexible + no class init then by the supervisor (adds complexity)

from time import sleep
from edwh_uuid7 import uuid7

from mpp import MalleableProfile
from fastapi import Response, FastAPI
from yarl import URL

from ..malc2 import HttpServerEmitter

app = FastAPI()
mp = MalleableProfile


# entrypoint
def run(listener_uuid: str):

    # make mp global to this module so we don't have to  read from it/pass everywhere constantly
    global mp
    # placeholder
    mp = MalleableProfile(profile="/home/ubuntu-dev/LongHaulC2/webbug_getonly.profile")
    print(mp)

    # dont register until mp is created.
    register_routes()

    import uvicorn

    # reload needs to be OFF.
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


###################################
# HTTP GET
###################################
"""
HTTP POST with CS is where task data is retrieved from the server.

"""


async def http_get():
    # placehodler  script locatiob

    # pass in block to respective class
    emitter = HttpServerEmitter(mp.http_get.server)

    # get the stuff we need from it
    headers = emitter.headers()
    body = emitter.output_bytes()

    # note, payload would need to be inserted somehwere here too.  Ex,
    # redis lookup for next task -> insert where print it

    # and construct the response
    return Response(content=body, headers=headers)


def register_routes():
    """
    Registeres routes. Prevents these being called on import as well.
    """
    app.add_api_route(
        path=str(URL(mp.http_get.uri.value)),
        endpoint=http_get,  # logic for endpoint here
        methods=["GET"],
        response_model=dict,
        tags=["items"],
    )

    # HTTP POST ROUTE
    app.add_api_route(
        path=str(URL(mp.http_post.uri.value)),
        endpoint=http_post,  # logic for endpoint here
        methods=["GET"],
        response_model=dict,
        tags=["items"],
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
