#pragma once

#include <vector>
#include <map>
#include "../../protocols/json/json.h"

int create_metadata(const std::map<std::string, std::string>& metadata, std::vector<unsigned char>& response_buffer);
nlohmann::json decode_msgpack_task(const std::string& task_as_msgpack_bytes);

int create_task_response(const std::string& implant_uuid, const std::string& task_uuid, const nlohmann::json& result_json, std::vector<uint8_t>& response_buffer);
//int create_task_response(const std::string& implant_uuid, const std::string& task_uuid, const std::vector<uint8_t>& binary_data, std::vector<uint8_t>& response_buffer);

//helpers
void add_text_result(nlohmann::json& result,const std::string& key,const std::string& value);
void add_bytes_result(nlohmann::json& result,const std::string& key,const std::string& value);