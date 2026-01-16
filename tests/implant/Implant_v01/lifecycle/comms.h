#pragma once
#include "../protocols/json/json.h"

nlohmann::json get(std::string implant_uuid);
int post(std::string implant_uuid, std::string output_data);