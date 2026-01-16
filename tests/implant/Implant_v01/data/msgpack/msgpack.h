#pragma once

#include <vector>
#include <map>
#include "../../protocols/json/json.h"

int create_metadata(const std::map<std::string, std::string>& metadata, std::vector<unsigned char>& response_buffer);
nlohmann::json decode_msgpack_task(const std::vector<uint8_t>& task_as_msgpack_bytes);