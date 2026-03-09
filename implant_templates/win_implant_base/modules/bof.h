#pragma once
#include "data/structs.h"
extern "C" { //tldr, compield in c, so we need to use those names, not the c++ mangled ones
	#include "libs/bof_launcher_api.h"
}

#include <vector>
#include <iostream>
#include "_debug/debug.h"

ModuleResult run_bof(std::vector<uint8_t> bof_bytes, const std::string& bof_args);