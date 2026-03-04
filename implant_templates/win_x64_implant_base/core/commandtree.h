
#include "../protocols/json/json.h"

//take in the mapped object, after converted from msgpack
nlohmann::json command_tree(nlohmann::json task_data);

//placeholder for  a beacon printf style func?
int send_to_server(std::string output);