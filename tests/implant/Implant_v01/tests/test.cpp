//test funcs
#include <iostream>
#include <vector>
#include <map>
#include <cassert>
#define TEST(name) std::cout << "[*] Testing: " << name << "..." << std::endl;
#define OVERLOAD(name) std::cout << "[>] Overload: " << name << "..." << std::endl;

#include "../data/msgpack/msgpack.h"
#include "../protocols/json/json.h"

void test_create_metadata() {
    TEST("create_metadata");

    std::map<std::string, std::string> fake_metadata;
    fake_metadata["some_value"] = "urmom";
    std::vector<unsigned char> packed_metadata;

    create_metadata(fake_metadata, packed_metadata);

    // 3. Unpack & check that data using nlohmann/json
    // We use from_msgpack to verify the bytes were written correctly
    nlohmann::json unpacked_json = nlohmann::json::from_msgpack(packed_metadata);

    for (auto& [key, value] : unpacked_json.items()) {
        std::cout << key << ": " << value << '\n';
    }

    assert(unpacked_json["some_value"] == "urmom");
    std::cout << "    -> PASSED" << std::endl;
}

void test_decode_msgpack_task() {
    TEST("decode_msgpack_task");

    // [dict -> msgpack -> hex] 
    // {"task_uuid": "some_uuid", "implant_uuid": "intended_target", "task":{"taskname":"somename", "args":{"arg1":"value1"}}}
    std::vector<uint8_t> task_as_msgpack_bytes = { 0x83,0xa9,0x74,0x61,0x73,0x6b,0x5f,0x75,0x75,0x69,0x64,0xa9,0x73,0x6f,0x6d,0x65,0x5f,0x75,0x75,0x69,0x64,0xac,0x69,0x6d,0x70,0x6c,0x61,0x6e,0x74,0x5f,0x75,0x75,0x69,0x64,0xaf,0x69,0x6e,0x74,0x65,0x6e,0x64,0x65,0x64,0x5f,0x74,0x61,0x72,0x67,0x65,0x74,0xa4,0x74,0x61,0x73,0x6b,0x82,0xa8,0x74,0x61,0x73,0x6b,0x6e,0x61,0x6d,0x65,0xa8,0x73,0x6f,0x6d,0x65,0x6e,0x61,0x6d,0x65,0xa4,0x61,0x72,0x67,0x73,0x81,0xa4,0x61,0x72,0x67,0x31,0xa6,0x76,0x61,0x6c,0x75,0x65,0x31 };

    nlohmann::json task_json = decode_msgpack_task(task_as_msgpack_bytes);

    for (auto& [key, value] : task_json.items()) {
        // .dump() prints the string representation of complex objects (like the nested task)
        std::cout << key << ": " << value.dump() << '\n';
    }

    assert(task_json["task_uuid"] == "some_uuid");
    assert(task_json["implant_uuid"] == "intended_target");
    assert(task_json["task"]["taskname"] == "somename");
    assert(task_json["task"]["args"]["arg1"] == "value1");

    std::cout << "    -> PASSED" << std::endl;
}

void test_create_task_response() {
    TEST("create_task_response (with overloads)");

    std::vector<uint8_t> buffer;

    // test 1: text
    OVERLOAD("Overload 1: data_type:text, data:text");
    create_task_response("00000000-0000-0000-0000-000000000000", "00000000-0000-0000-0000-000000000000", "Command successful", buffer);

    // Verify
    nlohmann::json j1 = nlohmann::json::from_msgpack(buffer);
    //std::cout << "Text Type: " << j1["result"]["data_type"] << "\n"; // "text"
    //std::cout << "Text Data: " << j1["result"]["data"] << "\n";      // "Command successful"
    
    assert(j1["implant_uuid"] == "00000000-0000-0000-0000-000000000000");
    assert(j1["task_uuid"] == "00000000-0000-0000-0000-000000000000");
    assert(j1["result"]["data_type"] == "text");
    assert(j1["result"]["data"] == "Command successful");
    std::cout << "    -> PASSED" << std::endl;

    // test 2: bin
    OVERLOAD("Overload 2: data_type:binary, data:binary")
    std::vector<uint8_t> binary_data = { 0xDE, 0xAD, 0xBE, 0xEF };
    create_task_response("impl-001", "task-B", binary_data, buffer);

    // Verify
    nlohmann::json j2 = nlohmann::json::from_msgpack(buffer);
    std::cout << "Bin Type:  " << j2["result"]["data_type"] << "\n"; // "bytes"

    assert(j2["result"]["data_type"] == "bytes");

    if (j2["result"]["data"].is_binary()) {
        std::vector<uint8_t> extracted_vec = j2["result"]["data"].get_binary();

        std::cout << "Bin Data: " << extracted_vec.size() << " bytes\n";

        // 3. Now it is a clean Vector vs Vector comparison
        assert(extracted_vec == binary_data);
    }

    std::cout << "    -> PASSED" << std::endl;
}

void test_all() {
    test_create_metadata();
    test_decode_msgpack_task();
    test_create_task_response();
}

