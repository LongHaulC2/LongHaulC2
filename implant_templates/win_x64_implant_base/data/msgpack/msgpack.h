#pragma once

#include <vector>
#include <queue>
#include "../protocols/json/json.h"

int create_batched_task_response(const std::string& implant_uuid, std::queue<nlohmann::json>& response_queue, std::vector<uint8_t>& response_buffer);
