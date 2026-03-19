
#include "protocols/json/json.h"
#include "_debug/debug.h"

//take in the mapped object, after converted from msgpack
nlohmann::json command_tree(nlohmann::json task_data);


bool IsStrategyValid(const std::string& strategy, const std::string& setting_key);