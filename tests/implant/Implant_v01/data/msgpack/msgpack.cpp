//the logic behind msgpack conversions

//from_msgpack -> whatever it returns it as

//whatever it returns it as -> msgpack

#include <iostream>
#include <vector>
#include <map>
#include <string>
#include "../../protocols/json/json.h"

using json = nlohmann::json;

/** * @brief Creates a msgpack metadata object.
 * @param metadata: A map of <std::string, std::string>.
 * @param response_buffer: A vector to append the response bytes to.
 * @return 0 success, 1 fail
*/
int create_metadata(const std::map<std::string, std::string>& metadata, std::vector<unsigned char>& response_buffer) {
    // Check if map is empty
    if (metadata.empty()) {
        return 1;
    }

    try {
        // 1. Convert Map -> JSON
        json j = metadata;

        // 2. Serialize JSON -> MsgPack Bytes
        std::vector<uint8_t> packed_bytes = json::to_msgpack(j);

        // 3. Append to the response buffer
        response_buffer.insert(response_buffer.end(), packed_bytes.begin(), packed_bytes.end());

        return 0;
    }
    catch (const std::exception& e) {
        std::cerr << "Packing failed: " << e.what() << std::endl;
        return 1;
    }
}

/** * @brief [msgpack -> json] Takes task msgpack bytes and turns them into a dynamic json object
 * @param task_as_msgpack_bytes: The data to turn into a json object
 * @return The json object (acts like a map/dict)
*/
nlohmann::json decode_msgpack_task(const std::vector<uint8_t>& task_as_msgpack_bytes) {
    // Decode MsgPack -> JSON Object
    // handles the nested maps automatically.
    // If input is invalid, this throws json::parse_error
    json task_data = json::from_msgpack(task_as_msgpack_bytes);

    // items() gives key/value iterator for the JSON object
    for (auto& [key, value] : task_data.items()) {
        // If the value is complex (like the nested "task" map), this prints it cleanly as a string representation
        std::cout << key << ": " << value.dump() << '\n';
    }

    return task_data;
}

/*
Task response structure

{"task_uuid":"1234", "implant_uuid": 9999, "result":{"data_type":"text", "data":"somedomain\bob"}}

*/

int create_task_response() {
    return 0;

}