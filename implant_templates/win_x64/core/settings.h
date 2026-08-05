/**
 * @file SettingsManager.h
 * @brief Defines a thread-safe Singleton class for managing application settings dynamically.
 */

#pragma once
#include <map>
#include <variant>
#include <string>
#include <vector>
#include <windows.h>
#include <mutex>
#include "_debug/debug.h"

/**
 * @typedef SettingValue
 * @brief Defines the variant type containing all permissible data types for settings.
 */
// 1. Define allowed types
//std::map<std::string, EgressFunc> and std::map<std::string, IngressFunc> are included as allowed types, so that we can store the strategy maps in the settings manager to get later. Kinda hacky
using SettingValue = std::variant<bool, int, double, HANDLE, std::string, std::vector<std::string>>;

/**
 * @class SettingsManager
 * @brief A thread-safe Singleton manager for storing and retrieving configuration settings.
 * * This class uses a std::map coupled with a std::variant (SettingValue) to store
 * mixed-type configuration variables associated with string keys. It utilizes
 * std::mutex to guarantee thread-safe read and write operations across the application.
 */
class SettingsManager {
public:
    // --- THE SINGLETON PART ---

    /**
     * @brief Accesses the global Singleton instance of the SettingsManager.
     * @return SettingsManager& A reference to the single, static instance of the class.
     */
    // This is the global access point. 
    // It creates the instance the first time it's called, and returns it forever after.
    static SettingsManager& instance() {
        static SettingsManager instance; // Guaranteed to be destroyed, instantiated on first use.
        return instance;
    }

    /**
     * @brief Deleted copy constructor to enforce Singleton pattern.
     */
    // Delete copy constructor and assignment operator to prevent duplicates
    SettingsManager(const SettingsManager&) = delete;

    /**
     * @brief Deleted assignment operator to enforce Singleton pattern.
     */
    void operator=(const SettingsManager&) = delete;


    // --- YOUR SETTINGS LOGIC (Same as before) ---

    /**
     * @brief Sets or updates a configuration setting.
     * @tparam T The data type of the value being stored. Must be supported by the SettingValue variant.
     * @param key The unique string identifier for the setting.
     * @param value The actual value to be stored in the map.
     */
    template <typename T>
    void set(const std::string& key, T value) {
        std::lock_guard<std::mutex> lock(settingsMutex_); // Lock before writing
        settingsMap_[key] = value;
    }

    /**
     * @brief Specialized overload to handle C-style string literals.
     * @param key The unique string identifier for the setting.
     * @param value A const char* string literal, which will be implicitly converted to std::string.
     */
    void set(const std::string& key, const char* value) {
        std::lock_guard<std::mutex> lock(settingsMutex_);
        settingsMap_[key] = std::string(value);
    }

    /**
     * @brief Retrieves a configuration setting safely.
     * @tparam T The expected data type of the retrieved value.
     * @param key The unique string identifier for the setting.
     * @param defaultValue The fallback value to return if the key is missing or the type mismatches.
     * @return T The stored value if successfully found and type-matched; otherwise, defaultValue.
     */
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
    /**
     * @brief Private constructor to prevent direct instantiation.
     */
    // Private Constructor: Only the instance() method can create this.
    //init's the class, which allows the instance to be available
    SettingsManager() {
    }

    std::map<std::string, SettingValue> settingsMap_; ///< Map holding the key-value configuration pairs.
    mutable std::mutex settingsMutex_;                ///< Mutex ensuring thread-safety for map operations.
};

/*
Usage:

#include "core/SettingsManager.h"
SettingsManager::instance().set("host_ip", "192.168.1.50");
int port = SettingsManager::instance().get<int>("port", 80);
*/