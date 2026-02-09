
#include <iostream>
#include <string>
#include <filesystem>

namespace fs = std::filesystem;

//not getting output for soem eraosn
std::string ls(std::string path) {
    std::string output;

    // Check if path exists and is a directory
    if (fs::exists(path) && fs::is_directory(path)) {

        // Loop through the directory (like 'ls')
        for (const auto& entry : fs::directory_iterator(path)) {

            // Print the filename
            //std::cout << entry.path().filename().string();
            output += entry.path().filename().string();

            // Optional: Add a suffix to indicate type (like 'ls -F')
            if (entry.is_directory()) {
                output += "/";
            }

            //add newline
            output += "\n";
        }

        if (output.empty()) {
            output = "There's seemingly no files here. Go look somewhere else.";
        }
    }

    else {
        return "Path `" + path + "` does not exist";
    }

    return output;
}