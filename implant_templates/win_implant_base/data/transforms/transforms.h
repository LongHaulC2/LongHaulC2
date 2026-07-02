#pragma once
#include <string>
#include "_debug/debug.h"

void transform_prepend(std::string& data, const std::string& value);
void undo_transform_prepend(std::string& data, const std::string& value);
void transform_append(std::string& data, const std::string& value);
void undo_transform_append(std::string& data, const std::string& value);
void xor_mask(std::string& data, const std::string& key);
void base64_encode_inplace(std::string& data);
void base64_decode_inplace(std::string& data);
void base64url_encode_inplace(std::string& data);
void base64url_decode_inplace(std::string& data);
void netbios_encode(std::string& data);
void netbios_decode(std::string& data);
void netbiosu_encode(std::string& data);
void netbiosu_decode(std::string& data);
void symcrypt_encrypt(std::string& data, const std::string& key);
void symcrypt_decrypt(std::string& data, const std::string& key);