#pragma once
#include <windows.h>
#include <iostream>
#include "protocols/json/json.h"
//struct to hold return type.  Move to somewhere where everything can access. maybe a structs.h
struct ModuleResult {
	nlohmann::json data;  // Holds whatever data may be needed here, str, dict, list, etc. 
	DWORD windows_error_code;   // 0 = success, anything else = error, used for windows api error codes. GUI/calling func can convert these if they want. 
};
//then to use this to get these: 
//auto [content, error] = urfunc(urarg);
//or:
/*
ModuleResult module_result = put_file(file_bytes, file_path);
std::string content = module_result.message;
DWORD windows_error_code = module_result.windows_error_code;
*/