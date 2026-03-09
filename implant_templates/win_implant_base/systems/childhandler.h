#pragma once

#include <string>
#include <unordered_map>
#include <mutex>
#include "protocols/json/json.h"
#include <windows.h>
#include <queue>
#include "_debug/debug.h"

/*
=============================
Child tracker Overview
=============================

Structs for tracking items:

 - ChildRouteType: The type of link we have to the child. 

 - ChildRouteInfo: The associated info that we need to know about the child

ChildHandler Class:

...


route_task_to_child_implant:
Our routing function, used to call the needed method for each child's connection type.

*/
// Define the available routing methods for child implants
enum ChildRouteType {
    ROUTE_SMB_PIPE,
    ROUTE_TCP_SOCKET // Placeholder for future TCP P2P
};

// The data required to establish and maintain a connection to a child
struct ChildRouteInfo {
    std::string child_uuid; 
    ChildRouteType route_type;

    // SMB Pipe Specifics
    std::wstring pipe_inbox;
    std::wstring pipe_outbox;

    //NOTE - NEVER CLOSE THESE HANDLES. These are handled by the ChildHandler class,
    //if you close them,they bug out/the conn to child is lost
    HANDLE h_pipe_inbox = INVALID_HANDLE_VALUE;
    HANDLE h_pipe_outbox = INVALID_HANDLE_VALUE;


    std::string original_link_task_uuid;
    std::string parent_uuid;
    std::string host_address;

    // TCP Specifics (for later)
    // std::string ip_address;
    // int port;
};

// Singleton class to manage the thread-safe routing mesh
class ChildHandler {
private:
    std::unordered_map<std::string, ChildRouteInfo> routing_table_;
    std::mutex table_mutex_;

    std::map<std::string, std::queue<nlohmann::json>> child_task_queues_;
    std::mutex queue_mutex_;

    // Private constructor for Singleton pattern
    ChildHandler() = default;

public:
    // Delete copy constructors to enforce Singleton
    ChildHandler(const ChildHandler&) = delete;
    ChildHandler& operator=(const ChildHandler&) = delete;

    // Global access point
    static ChildHandler& instance();

    // Thread-safe map operations
    void add_child(const std::string& uuid, const ChildRouteInfo& info);
    bool get_child(const std::string& uuid, ChildRouteInfo& out_info);
    bool remove_child(const std::string& uuid);
    std::unordered_map<std::string, ChildRouteInfo> get_all_children();
};
