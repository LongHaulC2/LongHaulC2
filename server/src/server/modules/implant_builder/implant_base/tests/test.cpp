//test funcs
#include <iostream>
#include <vector>
#include <map>
#include <cassert>
#include <string>
#include <stdexcept>

#define TEST(name) std::cout << "[*] Testing: " << name << "..." << std::endl;
#define OVERLOAD(name) std::cout << "[>] Overload: " << name << "..." << std::endl;

#include "../data/msgpack/msgpack.h"
#include "../protocols/json/json.h"
#include "../protocols/base64/base64.h"
#include "../data/transforms/transforms.h"
void test_create_metadata() {
    TEST("create_metadata");

    std::map<std::string, std::string> fake_metadata;
    fake_metadata["some_value"] = "urmom";
    std::vector<unsigned char> packed_metadata; //does this nee dto be uin8_t

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
    //std::vector<uint8_t> task_as_msgpack_bytes = { 0x83,0xa9,0x74,0x61,0x73,0x6b,0x5f,0x75,0x75,0x69,0x64,0xa9,0x73,0x6f,0x6d,0x65,0x5f,0x75,0x75,0x69,0x64,0xac,0x69,0x6d,0x70,0x6c,0x61,0x6e,0x74,0x5f,0x75,0x75,0x69,0x64,0xaf,0x69,0x6e,0x74,0x65,0x6e,0x64,0x65,0x64,0x5f,0x74,0x61,0x72,0x67,0x65,0x74,0xa4,0x74,0x61,0x73,0x6b,0x82,0xa8,0x74,0x61,0x73,0x6b,0x6e,0x61,0x6d,0x65,0xa8,0x73,0x6f,0x6d,0x65,0x6e,0x61,0x6d,0x65,0xa4,0x61,0x72,0x67,0x73,0x81,0xa4,0x61,0x72,0x67,0x31,0xa6,0x76,0x61,0x6c,0x75,0x65,0x31 };

    std::string task_as_msgpack_str = std::string(
        "\x83\xa9\x74\x61\x73\x6b\x5f\x75\x75\x69\x64\xa9\x73\x6f\x6d\x65"
        "\x5f\x75\x75\x69\x64\xac\x69\x6d\x70\x6c\x61\x6e\x74\x5f\x75\x75"
        "\x69\x64\xaf\x69\x6e\x74\x65\x6e\x64\x65\x64\x5f\x74\x61\x72\x67"
        "\x65\x74\xa4\x74\x61\x73\x6b\x82\xa8\x74\x61\x73\x6b\x6e\x61\x6d"
        "\x65\xa8\x73\x6f\x6d\x65\x6e\x61\x6d\x65\xa4\x61\x72\x67\x73\x81"
        "\xa4\x61\x72\x67\x31\xa6\x76\x61\x6c\x75\x65\x31",
        92 // Size is required if the data ever contains 0x00
    );

    nlohmann::json task_json = decode_msgpack_task(task_as_msgpack_str);

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


/*
================================
Transform Tests
================================
*/
void test_transform_prepend_append() {
    TEST("transform_prepend & transform_append (In-Place)");

    // --- PREPEND ---
    std::string data = "World";
    std::string prefix = "Hello ";

    // 1. Transform
    transform_prepend(data, prefix);
    assert(data == "Hello World");

    // 2. Undo
    undo_transform_prepend(data, prefix);
    assert(data == "World");

    // 3. Error Case (Undo too much)
    std::string short_data = "Hi";
    try {
        undo_transform_prepend(short_data, "LongPrefix");
        std::cerr << "(!) Failed to catch prepend underflow exception\n";
        assert(false);
    }
    catch (...) {
        // Expected
    }


    // --- APPEND ---
    std::string data2 = "Hello";
    std::string suffix = " World";

    // 1. Transform
    transform_append(data2, suffix);
    assert(data2 == "Hello World");

    // 2. Undo
    undo_transform_append(data2, suffix);
    assert(data2 == "Hello");

    std::cout << "    -> PASSED" << std::endl;
}

void test_transform_xor() {
    TEST("transform_xor (In-Place)");

    std::string data = "AAAA"; // 0x41 0x41 0x41 0x41
    // Key: 0x01, 0x02
    // Expected: 0x40 ('@'), 0x43 ('C'), 0x40 ('@'), 0x43 ('C')
    std::string key = "\x01\x02";

    // 1. Encrypt
    xor_mask(data, key);
    assert(data == "@C@C");

    // 2. Decrypt (XOR is symmetric)
    xor_mask(data, key);
    assert(data == "AAAA");

    std::cout << "    -> PASSED" << std::endl;
}

void test_transform_base64() {
    TEST("transform_base64 & base64url (In-Place)");

    // --- STANDARD BASE64 ---
    std::string raw = "hello world";

    // 1. Encode
    base64_encode_inplace(raw);
    // "hello world" -> "aGVsbG8gd29ybGQ="
    assert(raw == "aGVsbG8gd29ybGQ=");

    // 2. Decode
    base64_decode_inplace(raw);
    assert(raw == "hello world");


    // --- BASE64 URL ---
    // We need a test case that produces '+' or '/' to verify the URL-safe swap.
    // Binary sequence: 0xFB (11111011) -> First 6 bits are 111110 (62) -> '+' in std, '-' in URL
    std::string tricky_bin;
    tricky_bin.push_back((char)0xFB);
    tricky_bin.push_back((char)0xF0);

    // 1. Encode URL
    base64url_encode_inplace(tricky_bin);
    // Standard would be: "+/A="
    // URL should be: "-_A" (No padding, swapped chars)
    assert(raw.find('=') == std::string::npos); // Should have no padding
    assert(raw.find('+') == std::string::npos); // Should not have +

    // 2. Decode URL
    base64url_decode_inplace(tricky_bin);

    // Verify byte content matches original
    assert(tricky_bin.size() == 2);
    assert((unsigned char)tricky_bin[0] == 0xFB);
    assert((unsigned char)tricky_bin[1] == 0xF0);

    std::cout << "    -> PASSED" << std::endl;
}

void test_transform_netbios() {
    TEST("transform_netbios (lowercase & uppercase)");

    // --- NetBIOS (lowercase 'a') ---
    // 'A' is 0x41. High nibble 4, Low nibble 1.
    // 'a' + 4 = 'e'. 'a' + 1 = 'b'. Result "eb"
    std::string data = "A";

    // 1. Encode
    netbios_encode(data);
    assert(data == "eb");

    // 2. Decode
    netbios_decode(data);
    assert(data == "A");


    // --- NetBIOSU (uppercase 'A') ---
    // 'A' is 0x41. High 4, Low 1.
    // 'A' + 4 = 'E'. 'A' + 1 = 'B'. Result "EB"
    std::string data2 = "A";

    // 1. Encode
    netbiosu_encode(data2);
    assert(data2 == "EB");

    // 2. Decode
    netbiosu_decode(data2);
    assert(data2 == "A");

    std::cout << "    -> PASSED" << std::endl;
}


void test_all() {
    //msgpack/data
    test_create_metadata();
    test_decode_msgpack_task();
    test_create_task_response();
    //transforms
    test_transform_prepend_append();
    test_transform_xor();
    test_transform_base64();
    test_transform_netbios();
}

