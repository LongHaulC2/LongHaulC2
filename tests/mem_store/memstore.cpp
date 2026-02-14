#pragma once
#include <map>
#include <variant>
#include <string>
#include <vector>
#include <iostream>

//uses c types for simplicity, easier to do this, and just pass  in values from c++ types as needed.
void XOR(unsigned char* data, size_t data_size, const char* key, size_t key_size) {
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

class MemStore {
public:
    // --- THE SINGLETON PART ---

    // This is the global access point. 
    // It creates the instance the first time it's called, and returns it forever after.
    static MemStore& instance() {
        static MemStore instance; // Guaranteed to be destroyed, instantiated on first use.
        return instance;
    }

    // Delete copy constructor and assignment operator to prevent duplicates
    MemStore(const MemStore&) = delete;
    void operator=(const MemStore&) = delete;


    //note, call with std::move(data) to truly pass ownership. 
    //tldr, we don't want more copies of what is being stored, in memory for longer than they need to be
    void store(const std::string& key, std::vector<uint8_t> data) {
        //memoty store XOR. For now, xoring the data with the map key name lmao. Not great but its easy.
        //also - giving the vector directly to XOR to modify it, rather than creating a copy
        XOR(data.data(), data.size(), key.c_str(), key.size());

        std::cout << "XOR'd:" << std::endl;
        for (auto d : data) {
            std::cout << d;
        }

        //move is called again here, to move the passed data, to the key, rather than copying. 
        memstore_map_[key] = std::move(data);
    }


    //overload for if we want to store strings/text? Can also just convert back to string if we know type... maybe later. 
    //void set(const std::string& key, std::vector<uint8_t> data) {
    //    memstore_map_[key] = value;
    //}

    std::vector<uint8_t> get(const std::string& key) const {
        auto it = memstore_map_.find(key);

        if (it != memstore_map_.end()) {
            std::vector<uint8_t> data{ it->second.begin(), it->second.end() };
            XOR(&data[0], data.size(), key.c_str(), key.size());

            return data;
        }
        return {};
    }

private:
    // Private Constructor: Only the instance() method can create this.
    //init's the class, which allows the instance to be available
    MemStore() {
    }

    std::map<std::string, std::vector<uint8_t>> memstore_map_;
};

/*
Usage:

#include "control/SettingsManager.h"
SettingsManager::instance().set("host_ip", "192.168.1.50");
int port = SettingsManager::instance().get<int>("port", 80);
*/


int main() {
    std::string data{ "Somedat that no one really cares about hopefully the quick brown fox jumps over the lazy dog. " };
    std::vector<uint8_t> data_before = { data.begin(), data.end()};
    std::cout << "Before:" << std::endl;
    for (auto d : data_before) {
        std::cout << d;
    }
    MemStore::instance().store("mydata", data_before);

    std::vector<uint8_t> data_after =  MemStore::instance().get("mydata");

    std::cout << "After:" << std::endl;
    for (auto d : data_after) {
        std::cout << d;
    }

}