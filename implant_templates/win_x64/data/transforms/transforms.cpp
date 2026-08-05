#include <string>
#include <vector>
#include <bcrypt.h>
#include "protocols/base64/base64.h"
#include "defense/winapi.h"

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

// ==========================================
// AES-256-GCM via Windows BCrypt (In-Place)
// ==========================================

static constexpr ULONG SYMCRYPT_NONCE_LEN = 12;
static constexpr ULONG SYMCRYPT_TAG_LEN   = 16;
static constexpr ULONG SYMCRYPT_KEY_LEN   = 32;

void symcrypt_encrypt(std::string& data, const std::string& key) {
    if (key.size() != SYMCRYPT_KEY_LEN) {
        DEBUG_LOG("symcrypt_encrypt: key must be 32 bytes");
        return;
    }

    WinApi::EnsureModuleLoaded("bcrypt.dll");

    BCRYPT_ALG_HANDLE hAlg = nullptr;
    BCRYPT_KEY_HANDLE hKey = nullptr;

    NTSTATUS status = WinApi::BCryptOpenAlgorithmProvider(&hAlg, BCRYPT_AES_ALGORITHM, nullptr, 0);
    if (status != 0) { DEBUG_LOG("symcrypt_encrypt: BCryptOpenAlgorithmProvider failed"); return; }

    status = WinApi::BCryptSetProperty(hAlg, BCRYPT_CHAINING_MODE,
        (PUCHAR)BCRYPT_CHAIN_MODE_GCM, sizeof(BCRYPT_CHAIN_MODE_GCM), 0);
    if (status != 0) { WinApi::BCryptCloseAlgorithmProvider(hAlg, 0); return; }

    status = WinApi::BCryptGenerateSymmetricKey(hAlg, &hKey, nullptr, 0,
        (PUCHAR)key.data(), SYMCRYPT_KEY_LEN, 0);
    if (status != 0) { WinApi::BCryptCloseAlgorithmProvider(hAlg, 0); return; }

    // Generate random nonce
    UCHAR nonce[SYMCRYPT_NONCE_LEN];
    status = WinApi::BCryptGenRandom(nullptr, nonce, SYMCRYPT_NONCE_LEN, BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    if (status != 0) {
        WinApi::BCryptDestroyKey(hKey);
        WinApi::BCryptCloseAlgorithmProvider(hAlg, 0);
        return;
    }

    UCHAR tag[SYMCRYPT_TAG_LEN];
    BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO authInfo;
    BCRYPT_INIT_AUTH_MODE_INFO(authInfo);
    authInfo.pbNonce = nonce;
    authInfo.cbNonce = SYMCRYPT_NONCE_LEN;
    authInfo.pbTag   = tag;
    authInfo.cbTag   = SYMCRYPT_TAG_LEN;

    ULONG plainLen = static_cast<ULONG>(data.size());
    std::string ciphertext(plainLen, '\0');
    ULONG bytesWritten = 0;

    status = WinApi::BCryptEncrypt(hKey,
        (PUCHAR)data.data(), plainLen,
        &authInfo, nullptr, 0,
        (PUCHAR)ciphertext.data(), plainLen, &bytesWritten, 0);

    WinApi::BCryptDestroyKey(hKey);
    WinApi::BCryptCloseAlgorithmProvider(hAlg, 0);

    if (status != 0) {
        DEBUG_LOG("symcrypt_encrypt: BCryptEncrypt failed");
        return;
    }

    // Output: [nonce][tag][ciphertext]
    std::string result;
    result.reserve(SYMCRYPT_NONCE_LEN + SYMCRYPT_TAG_LEN + bytesWritten);
    result.append(reinterpret_cast<char*>(nonce), SYMCRYPT_NONCE_LEN);
    result.append(reinterpret_cast<char*>(tag), SYMCRYPT_TAG_LEN);
    result.append(ciphertext.data(), bytesWritten);
    data = std::move(result);
}

void symcrypt_decrypt(std::string& data, const std::string& key) {
    const ULONG overhead = SYMCRYPT_NONCE_LEN + SYMCRYPT_TAG_LEN;
    if (key.size() != SYMCRYPT_KEY_LEN) {
        DEBUG_LOG("symcrypt_decrypt: key must be 32 bytes");
        data.clear();
        return;
    }
    if (data.size() < overhead) {
        DEBUG_LOG("symcrypt_decrypt: data too short");
        data.clear();
        return;
    }

    WinApi::EnsureModuleLoaded("bcrypt.dll");

    BCRYPT_ALG_HANDLE hAlg = nullptr;
    BCRYPT_KEY_HANDLE hKey = nullptr;

    NTSTATUS status = WinApi::BCryptOpenAlgorithmProvider(&hAlg, BCRYPT_AES_ALGORITHM, nullptr, 0);
    if (status != 0) { data.clear(); return; }

    status = WinApi::BCryptSetProperty(hAlg, BCRYPT_CHAINING_MODE,
        (PUCHAR)BCRYPT_CHAIN_MODE_GCM, sizeof(BCRYPT_CHAIN_MODE_GCM), 0);
    if (status != 0) { WinApi::BCryptCloseAlgorithmProvider(hAlg, 0); data.clear(); return; }

    status = WinApi::BCryptGenerateSymmetricKey(hAlg, &hKey, nullptr, 0,
        (PUCHAR)key.data(), SYMCRYPT_KEY_LEN, 0);
    if (status != 0) { WinApi::BCryptCloseAlgorithmProvider(hAlg, 0); data.clear(); return; }

    // Parse: [nonce (12)][tag (16)][ciphertext]
    UCHAR nonce[SYMCRYPT_NONCE_LEN];
    UCHAR tag[SYMCRYPT_TAG_LEN];
    memcpy(nonce, data.data(), SYMCRYPT_NONCE_LEN);
    memcpy(tag, data.data() + SYMCRYPT_NONCE_LEN, SYMCRYPT_TAG_LEN);

    ULONG ctLen = static_cast<ULONG>(data.size() - overhead);
    const PUCHAR ctPtr = (PUCHAR)data.data() + overhead;

    BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO authInfo;
    BCRYPT_INIT_AUTH_MODE_INFO(authInfo);
    authInfo.pbNonce = nonce;
    authInfo.cbNonce = SYMCRYPT_NONCE_LEN;
    authInfo.pbTag   = tag;
    authInfo.cbTag   = SYMCRYPT_TAG_LEN;

    std::string plaintext(ctLen, '\0');
    ULONG bytesWritten = 0;

    status = WinApi::BCryptDecrypt(hKey,
        ctPtr, ctLen,
        &authInfo, nullptr, 0,
        (PUCHAR)plaintext.data(), ctLen, &bytesWritten, 0);

    WinApi::BCryptDestroyKey(hKey);
    WinApi::BCryptCloseAlgorithmProvider(hAlg, 0);

    if (status != 0) {
        DEBUG_LOG("symcrypt_decrypt: BCryptDecrypt failed (bad key or tampered data)");
        data.clear();
        return;
    }

    plaintext.resize(bytesWritten);
    data = std::move(plaintext);
}