
from yarl import URL
import logging 

server_log = logging.getLogger("server")

#todo: find a way to get args/startup things to this later, for more dynamic url generation
#ex, python3 client --host https://127.0.0.1:1234
def generate_url(uri:str) -> str:
    '''
    Generates a full URL for requests. Handles the schema, and IP/Address of the API. 
    
    :param uri: Description
    :type uri: str
    '''

    # removes leading slash on URI, which YARL does not like.
    # Ex, if uri == "/some/endpoint", it will convert to this: "some/endpoint"
    if uri.startswith("/"):
        uri = uri[1:]

    HOST = "http://10.0.0.30:45045"

    url = URL(HOST) / uri
    server_log.debug(f"Generated URL: {url}")
    return str(url)