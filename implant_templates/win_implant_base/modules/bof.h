#pragma once
#include "data/structs.h"
extern "C" {
	#include "libs/bof_launcher_api.h"
}

#include <vector>
#include "_debug/debug.h"

ModuleResult run_bof(std::vector<uint8_t> bof_bytes, const std::string& bof_args);