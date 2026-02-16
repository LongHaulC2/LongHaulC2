#include <map>
#include <string>
#include "../data/structs.h"
void populate_metadata(std::map<std::string, std::string>& metadata);
ModuleResult get_current_user();
ModuleResult get_computer_name();
ModuleResult get_current_process_name();
ModuleResult get_current_process_pid();
ModuleResult get_ip_address();