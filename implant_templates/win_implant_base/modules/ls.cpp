
#include <string>
#include <filesystem>
#include <windows.h>
#include "data/structs.h"
#include "ls.h"
#include "_debug/debug.h"

namespace fs = std::filesystem;

ModuleResult ls(std::string path) {
    std::string output;

    if (fs::exists(path) && fs::is_directory(path)) {
        for (const auto& entry : fs::directory_iterator(path)) {
            output += entry.path().filename().string();
            if (entry.is_directory()) {
                output += "/";
            }
            output += "\n";
        }

        if (output.empty()) {
            output = "There's seemingly no files here. Go look somewhere else.";
        }
    }
    else {
        return { "", ERROR_PATH_NOT_FOUND};
    }

    return { output, ERROR_SUCCESS };
}