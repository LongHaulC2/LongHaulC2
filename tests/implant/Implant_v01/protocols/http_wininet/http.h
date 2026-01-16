#pragma once

#include <iostream>
#include <vector>
/**
 * @brief Makes a HTTP_GET style request to the server
 *
 * Reads the settings file, validates values, and applies defaults
 * where fields are missing.
 *
 * @param headers: A vector of headers to include in the request.
 * @param (out) response: A vector that the response from the server is stored in.
 * @returns BOOL: True for success, else fail
 */
bool HTTP_GET(std::vector<std::wstring>& headers, std::vector<uint8_t>& response);
bool HTTP_POST( std::string data, std::vector<std::wstring>& headers, std::vector<uint8_t>& response);