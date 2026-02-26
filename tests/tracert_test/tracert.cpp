#include <windows.h>
#include <iphlpapi.h>
#include <icmpapi.h>
#include <iostream>

#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "ws2_32.lib")


void QuickTrace(const char* targetIP, int maxHops) {
    HANDLE hIcmpFile = IcmpCreateFile();
    if (hIcmpFile == INVALID_HANDLE_VALUE) return;

    char sendData[] = "HCKD_PROBE"; // Custom data payload
    LPVOID replyBuffer = (char*)malloc(sizeof(ICMP_ECHO_REPLY) + sizeof(sendData));

    IP_OPTION_INFORMATION options = { 0 };
    options.Tos = 0;
    options.Flags = 0;

    std::cout << "Tracing " << targetIP << " up to " << maxHops << " hops...\n";

    for (int ttl = 1; ttl <= maxHops; ttl++) {
        options.Ttl = (UCHAR)ttl; // Set custom TTL

        DWORD dwRetVal = IcmpSendEcho(
            hIcmpFile,
            inet_addr(targetIP),
            sendData, sizeof(sendData),
            &options, replyBuffer,
            sizeof(ICMP_ECHO_REPLY) + sizeof(sendData),
            1000 // Timeout 1s
        );

        PICMP_ECHO_REPLY pEchoReply = (PICMP_ECHO_REPLY)replyBuffer;
        struct in_addr addr;
        addr.S_un.S_addr = pEchoReply->Address;

        if (dwRetVal > 0) {
            std::cout << "Hop " << ttl << ": " << inet_ntoa(addr);

            // If we got a reply from the target, we're done
            if (pEchoReply->Status == IP_SUCCESS) {
                std::cout << " [Target Reached]" << std::endl;
                break;
            }
            std::cout << " [Time Exceeded/Other]" << std::endl;
        }
        else {
            std::cout << "Hop " << ttl << ": Request Timed Out" << std::endl;
        }
    }

    free(replyBuffer);
    IcmpCloseHandle(hIcmpFile);
}

/*
Test tracert for some disovery stuff

Idea is that maybe this could be used to get all nodes the c2 implant takes. 
*/

int main() {
    const char* dest = "1.1.1.1";
    QuickTrace(dest, 50);
}
