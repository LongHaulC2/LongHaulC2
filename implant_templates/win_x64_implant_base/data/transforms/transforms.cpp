#include <string>
#include <vector>
#include <stdexcept>
#include <algorithm> // for std::transform if needed

#include <iostream>
#include "../../protocols/base64/base64.h"

// ==========================================
// Prepend / Append (In-Place)
// ==========================================

void transform_prepend(std::string& data, const std::string& value) {
    // Inserts value at index 0. This involves moving existing memory.
    data.insert(0, value);
}

// void undo_transform_prepend(std::string& data, const std::string& value) {
//     if (data.size() < value.size()) {
//         throw std::runtime_error("undo_prepend: Data shorter than value");
//     }
//     std::cout << "undo_transform_prepend: Before: " << data << std::endl;
//     // Erase from index 0, count of value.size()
//     data.erase(0, value.size());
//     std::cout << "undo_transform_prepend: After: " << data << std::endl;

// }

void undo_transform_prepend(std::string& data, const std::string& value) {
    if (!data.starts_with(value)) {
        std::cerr << "undo_transform_prepend: prefix mismatch\n";
        std::cerr << "Expected prefix:\n" << value << "\n\n";
        std::cerr << "Actual prefix:\n" 
                  << data.substr(0, value.size()) << "\n";
        throw std::runtime_error("undo_prepend: prefix does not match");
    }
    data.erase(0, value.size());
}


void transform_append(std::string& data, const std::string& value) {
    data += value;
}

void undo_transform_append(std::string& data, const std::string& value) {
    if (data.size() < value.size()) {
        throw std::runtime_error("undo_append: Data shorter than value");
    }
    std::cout << "undo_transform_append: Before: " << data << std::endl;

    // Resize to cut off the end
    data.resize(data.size() - value.size());
    std::cout << "undo_transform_append: After: " << data << std::endl;

}

// ==========================================
// XOR (In-Place)
// ==========================================

void xor_mask(std::string& data, const std::string& key) {
    if (key.empty()) return; // Or throw error based on preference

    size_t key_len = key.size();
    for (size_t i = 0; i < data.size(); ++i) {
        data[i] ^= key[i % key_len];
    }
}

// ==========================================
// Base64 Wrappers (In-Place)
// ==========================================

void base64_encode_inplace(std::string& data) {
    // Since the lib returns a new string, we assign it back.
    // std::move optimizes the assignment.
    data = base64_encode(data, false);
}



void base64_decode_inplace(std::string& data) {
    data = base64_decode(data, false);
}

// void base64url_encode_inplace(std::string& data) {
//     // 1. Encode with URL safe chars
//     data = base64_encode(data, true);

//     // 2. Remove padding '=' from the end
//     while (!data.empty() && data.back() == '=') {
//         data.pop_back();
//     }
// }
//hotfic
void base64url_encode_inplace(std::string& data) {
    // 1. Encode with URL safe chars
    // This library appears to use '.' for padding when bool url_safe=true
    data = base64_encode(data, true);

    // 2. Remove padding (check for BOTH '=' and '.')
    while (!data.empty() && (data.back() == '=' || data.back() == '.')) {
        data.pop_back();
    }
}

void base64url_decode_inplace(std::string& data) {
    // 1. Restore padding
    while (data.length() % 4 != 0) {
        data.push_back('=');
    }

    // 2. Fix alphabet (since your decode lib header doesn't imply it handles URL alphabet automatically)
    // Replace '-' with '+' and '_' with '/'
    for (char& c : data) {
        if (c == '-') c = '+';
        else if (c == '_') c = '/';
    }

    // 3. Decode
    data = base64_decode(data, false);
}

// ==========================================
// NetBIOS (In-Place / Optimized Swap)
// ==========================================

void netbios_encode(std::string& data) {
    std::string temp;
    temp.reserve(data.size() * 2);

    for (unsigned char b : data) {
        unsigned char high = (b >> 4) & 0x0F;
        unsigned char low = b & 0x0F;
        temp.push_back('a' + high);
        temp.push_back('a' + low);
    }

    // Efficiently swap the temp buffer into data
    data = std::move(temp);
}

void netbios_decode(std::string& data) {
    if (data.length() % 2 != 0) {
        throw std::runtime_error("netbios_decode: Invalid length");
    }

    // We can do this truly in-place by maintaining a read and write index
    // because the data shrinks by half.
    size_t write_idx = 0;

    for (size_t read_idx = 0; read_idx < data.length(); read_idx += 2) {
        unsigned char high = static_cast<unsigned char>(data[read_idx]) - 'a';
        unsigned char low = static_cast<unsigned char>(data[read_idx + 1]) - 'a';

        data[write_idx++] = (high << 4) | low;
    }

    // Shrink the string to the new size
    data.resize(write_idx);
}

// ==========================================
// NetBIOSU (In-Place / Optimized Swap)
// ==========================================

void netbiosu_encode(std::string& data) {
    std::string temp;
    temp.reserve(data.size() * 2);

    for (unsigned char b : data) {
        unsigned char high = (b >> 4) & 0x0F;
        unsigned char low = b & 0x0F;
        temp.push_back('A' + high);
        temp.push_back('A' + low);
    }
    data = std::move(temp);
}

void netbiosu_decode(std::string& data) {
    if (data.length() % 2 != 0) {
        throw std::runtime_error("netbiosu_decode: Invalid length");
    }

    size_t write_idx = 0;
    for (size_t read_idx = 0; read_idx < data.length(); read_idx += 2) {
        unsigned char high = static_cast<unsigned char>(data[read_idx]) - 'A';
        unsigned char low = static_cast<unsigned char>(data[read_idx + 1]) - 'A';
        data[write_idx++] = (high << 4) | low;
    }
    data.resize(write_idx);
}