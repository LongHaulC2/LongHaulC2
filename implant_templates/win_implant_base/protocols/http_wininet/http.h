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
bool HTTP_GET(const std::wstring& callback_host, int callback_port, std::wstring http_verb, const std::wstring& uri, const std::vector<std::wstring>& headers, std::string& request_body, std::string& response);
bool HTTP_POST(const std::wstring& callback_host, int callback_port, std::wstring http_verb, const std::wstring& uri, const std::vector<std::wstring>& headers, std::string& request_body, std::string& response);