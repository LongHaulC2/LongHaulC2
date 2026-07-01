#pragma once
#include <windows.h>
#include "protocols/json/json.h"

struct ModuleResult {
	nlohmann::json data;
	DWORD windows_error_code;
};