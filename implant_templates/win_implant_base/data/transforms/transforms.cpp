#include <string>
#include <vector>
#include "protocols/base64/base64.h"
#include "_debug/debug.h"

// ==========================================
// Prepend / Append (In-Place)
// ==========================================

void transform_prepend(std::string& data, const std::string& value) {
    data.insert(0, value);
}

void undo_transform_prepend(std::string& data, const std::string& value) {
    if (data.size() < value.size() || !data.starts_with(value)) {
        DEBUG_LOG("undo_transform_prepend: prefix mismatch, erasing by length");
        if (data.size() >= value.size()) {
            data.erase(0, value.size());
        }
        return;
    }
    data.erase(0, value.size());
}


void transform_append(std::string& data, const std::string& value) {
    data += value;
}

void undo_transform_append(std::string& data, const std::string& value) {
    if (data.size() < value.size()) {
        DEBUG_LOG("undo_transform_append: data shorter than suffix, skipping");
        return;
    }
    data.resize(data.size() - value.size());
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
        DEBUG_LOG("netbios_decode: odd length input, truncating last byte");
        data.resize(data.length() - 1);
    }
    if (data.empty()) return;

    size_t write_idx = 0;
    for (size_t read_idx = 0; read_idx < data.length(); read_idx += 2) {
        unsigned char high = static_cast<unsigned char>(data[read_idx]) - 'a';
        unsigned char low = static_cast<unsigned char>(data[read_idx + 1]) - 'a';
        data[write_idx++] = (high << 4) | low;
    }
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
        DEBUG_LOG("netbiosu_decode: odd length input, truncating last byte");
        data.resize(data.length() - 1);
    }
    if (data.empty()) return;

    size_t write_idx = 0;
    for (size_t read_idx = 0; read_idx < data.length(); read_idx += 2) {
        unsigned char high = static_cast<unsigned char>(data[read_idx]) - 'A';
        unsigned char low = static_cast<unsigned char>(data[read_idx + 1]) - 'A';
        data[write_idx++] = (high << 4) | low;
    }
    data.resize(write_idx);
}