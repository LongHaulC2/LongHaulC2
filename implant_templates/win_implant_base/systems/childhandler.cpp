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
#include "_debug/debug.h"

//singleton for this
ChildHandler& ChildHandler::instance() {
    DEBUG_LOG("[ChildHandler::instance] Accessing/Initializing Singleton Instance");
    static ChildHandler _instance;
    return _instance;
}

void ChildHandler::add_child(const std::string& uuid, const ChildRouteInfo& info) {
    DEBUG_LOG("[ChildHandler::add_child] Registering child UUID: " + uuid);
    std::lock_guard<std::mutex> lock(table_mutex_);
    routing_table_[uuid] = info;
}

bool ChildHandler::get_child(const std::string& uuid, ChildRouteInfo& out_info) {
    DEBUG_LOG("[ChildHandler::get_child] Looking up routing info for UUID: " + uuid);
    std::lock_guard<std::mutex> lock(table_mutex_);

    auto it = routing_table_.find(uuid);
    if (it != routing_table_.end()) {
        DEBUG_LOG("[ChildHandler::get_child] Found child: " + uuid);
        out_info = it->second;
        return true; // Found it, out_info is populated
    }

    DEBUG_LOG("[ChildHandler::get_child] FAILED to find child: " + uuid);
    return false; // Child not in the routing table
}

bool ChildHandler::remove_child(const std::string& uuid) {
    DEBUG_LOG("[ChildHandler::remove_child] Removing child: " + uuid);
    std::lock_guard<std::mutex> lock(table_mutex_);

    // erase() returns the number of elements removed (1 if found, 0 if not)
    bool removed = routing_table_.erase(uuid) > 0;
    if (removed) {
        DEBUG_LOG("[ChildHandler::remove_child] Successfully removed: " + uuid);
    } else {
        DEBUG_LOG("[ChildHandler::remove_child] Could not remove (UUID not found): " + uuid);
    }
    return removed;
}

std::unordered_map<std::string, ChildRouteInfo> ChildHandler::get_all_children() {
    DEBUG_LOG("[ChildHandler::get_all_children] Dumping entire routing table. Total children: " + std::to_string(routing_table_.size()));
    return routing_table_;
}