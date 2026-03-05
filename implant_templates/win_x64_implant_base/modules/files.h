#pragma once
#include <string>
#include "../data/structs.h"

ModuleResult get_file(std::string file_path);
ModuleResult put_file(std::vector<uint8_t> file_contents, std::string file_path);