#pragma once
#include <map>
#include <variant>
#include <string>
#include <vector>
#include <iostream>
#include "c2.h" //ingress,egress definitions
#include <windows.h>
#include <mutex>
#include "_debug/debug.h"

// 1. Define allowed types
//std::map<std::string, EgressFunc> and std::map<std::string, IngressFunc> are included as allowed types, so that we can store the strategy maps in the settings manager to get later. Kinda hacky
using SettingValue = std::variant<bool, int, double, HANDLE, std::string, std::vector<std::string>>;

class SettingsManager {
public:
    // --- THE SINGLETON PART ---

    // This is the global access point. 
    // It creates the instance the first time it's called, and returns it forever after.
    static SettingsManager& instance() {
        static SettingsManager instance; // Guaranteed to be destroyed, instantiated on first use.
        return instance;
    }

    // Delete copy constructor and assignment operator to prevent duplicates
    SettingsManager(const SettingsManager&) = delete;
    void operator=(const SettingsManager&) = delete;


    // --- YOUR SETTINGS LOGIC (Same as before) ---

    template <typename T>
    void set(const std::string& key, T value) {
        std::lock_guard<std::mutex> lock(settingsMutex_); // Lock before writing
        settingsMap_[key] = value;
    }

    // Special overload for string literals
    void set(const std::string& key, const char* value) {
        settingsMap_[key] = std::string(value);
    }

    template <typename T>
    T get(const std::string& key, const T& defaultValue) const {
        std::lock_guard<std::mutex> lock(settingsMutex_); // Lock before reading
        auto it = settingsMap_.find(key);
        //if not found
        if (it == settingsMap_.end()) {
            return defaultValue;
        }
        //if found
        if (const T* valPtr = std::get_if<T>(&(it->second))) {
            return *valPtr;
        }
            
        return defaultValue;
    }

private:
    // Private Constructor: Only the instance() method can create this.
    //init's the class, which allows the instance to be available
    SettingsManager() {
    }

    std::map<std::string, SettingValue> settingsMap_;
    mutable std::mutex settingsMutex_;
};

/*
Usage:

#include "core/SettingsManager.h"
SettingsManager::instance().set("host_ip", "192.168.1.50");
int port = SettingsManager::instance().get<int>("port", 80);
*/