#include <iostream>
#include <vector>
#include <string>
#include "../../protocols/json/json.h"
#include <queue>


int create_batched_task_response(const std::string& implant_uuid, std::queue<nlohmann::json>& response_queue, std::vector<uint8_t>& response_buffer) {
    try {
        // Create a root JSON array to hold all queued task responses
        nlohmann::json batched_responses = nlohmann::json::array();

        // Drain the queue
        while (!response_queue.empty()) {
            nlohmann::json queued_item = response_queue.front();
            response_queue.pop();

            nlohmann::json single_response;
            single_response["implant_uuid"] = implant_uuid;

            // Extract the task_uuid if it's baked into the queued item
            if (queued_item.contains("task_uuid")) {
                single_response["task_uuid"] = queued_item["task_uuid"];
                // Optional: remove task_uuid from the result payload to avoid duplication
                queued_item.erase("task_uuid");
            }
            else {
                single_response["task_uuid"] = "unknown_task";
            }

            // Assign the rest of the queued item as the task result
            single_response["result"] = queued_item;

            // Push this formatted object into our main array
            batched_responses.push_back(single_response);
        }

        // Pack the entire array of objects into MsgPack
        response_buffer = nlohmann::json::to_msgpack(batched_responses);
        return 0;
    }
    catch (const std::exception& e) {
        std::cerr << "Batched packing error: " << e.what() << "\n";
        return 1;
    }
}


