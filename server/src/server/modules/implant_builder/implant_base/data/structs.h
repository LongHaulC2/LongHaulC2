#pragma once
#include <windows.h>

//struct to hold return type.  Move to somewhere where everything can access. maybe a structs.h
struct ModuleResult {
	std::string data;  // Holds whatever text data may be needed here
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