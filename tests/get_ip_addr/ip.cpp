#include <iostream>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <iphlpapi.h>

#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "ws2_32.lib")

int main() {
    ULONG flags = GAA_FLAG_INCLUDE_PREFIX;
    ULONG family = AF_INET; // AF_INET6 for IPv6
    ULONG bufferSize = 15000;

    PIP_ADAPTER_ADDRESSES adapters = (IP_ADAPTER_ADDRESSES*)malloc(bufferSize);

    if (GetAdaptersAddresses(family, flags, NULL, adapters, &bufferSize) == NO_ERROR) {

        for (PIP_ADAPTER_ADDRESSES adapter = adapters; adapter != NULL; adapter = adapter->Next) {


            //skip disconnected/disabled adapters
            if (adapter->OperStatus != IfOperStatusUp) {
                continue;
            }

            //skip loopback
            if (adapter->IfType == IF_TYPE_SOFTWARE_LOOPBACK) {
                continue;
            }

            for (PIP_ADAPTER_UNICAST_ADDRESS ua = adapter->FirstUnicastAddress;
                ua != NULL;
                ua = ua->Next) {

                SOCKADDR* sa = ua->Address.lpSockaddr;

                char ipStr[INET6_ADDRSTRLEN];

                if (sa->sa_family == AF_INET) {
                    sockaddr_in* ipv4 = (sockaddr_in*)sa;

                    inet_ntop(AF_INET, &ipv4->sin_addr, ipStr, sizeof(ipStr));

                    std::cout << "IP: " << ipStr
                        << "/" << (int)ua->OnLinkPrefixLength
                        << std::endl;
                }
            }
        }
    }

    free(adapters);
    getchar();

    return 0;

}