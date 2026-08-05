#pragma once

#include <vector>
#include <queue>
#include "protocols/json/json.h"
#include "_debug/debug.h"

nlohmann::json create_batched_task_json(const std::string& implant_uuid, std::queue<nlohmann::json>& response_queue);