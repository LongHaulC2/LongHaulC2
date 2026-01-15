//test funcs
#include <iostream>
#include <vector>
#include <map>
#include <cassert>
#define TEST(name) std::cout << "[*] Testing: " << name << "..." << std::endl;


#include "../data/msgpack/msgpack.h"
#include "../protocols/msgpack23/msgpack23.h"
void test_create_metadata() {
    TEST("create_metadata");

    //pack 
    std::map<std::string, std::string> fake_metadata;
    fake_metadata["some_value"] = "urmom";
    std::vector<unsigned char> packed_metadata;

    //function used to pack it
    create_metadata(fake_metadata, packed_metadata);

    //unpack that data now
    std::map<std::string, std::string> unpacked_metadata;
    msgpack23::Unpacker unpacker{ packed_metadata };
    unpacker(unpacked_metadata);

    for (auto const& [key, value] : unpacked_metadata) {
        std::cout << key << ": " << value << '\n';
    }

    assert(unpacked_metadata["some_value"] == "urmom");
    std::cout << "    -> PASSED" << std::endl;
}

void test() {
    test_create_metadata();
}

