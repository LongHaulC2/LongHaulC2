//tldr, this is needed so it compiles
#define WIN32_LEAN_AND_MEAN
#ifndef WINVER
#define WINVER 0x0601        // Target Windows 7 or higher
#endif
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif

#include <winsock2.h>
#include <ws2tcpip.h>
#include <iphlpapi.h>
#include <netioapi.h> //Table2
#include "../data/structs.h"
#include "discover.h"
#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "ws2_32.lib")


//idea, name this "neighbor discovery" or something, for each enightbor, addd it to a map of ipand mac,and send back in data. 
// this allows for better parsing/neighbor discovery/a consistent return so the server knows how to handle it, and pass to neo4j.
ModuleResult passive_arp_discovery() {
    //https://learn.microsoft.com/en-us/windows/win32/api/netioapi/ns-netioapi-mib_ipnet_row2
    PMIB_IPNET_TABLE2 pTable = nullptr;

    std::string neighbors = {};

    if (GetIpNetTable2(AF_UNSPEC, &pTable) == NO_ERROR) {
        for (ULONG i = 0; i < pTable->NumEntries; i++) {
            MIB_IPNET_ROW2 row = pTable->Table[i];

            // ONLY show entries that are confirmed reachable
            //https://learn.microsoft.com/en-us/windows/win32/api/netioapi/nf-netioapi-getipnettable2
            if (row.State == NlnsReachable) {
                wchar_t ipStr[64];
                InetNtopW(row.Address.si_family, &row.Address.Ipv4.sin_addr, ipStr, 64);


                std::wstring w_string_ip(ipStr);
                std::string string_ip(w_string_ip.begin(), w_string_ip.end());

                neighbors += string_ip;
                neighbors += "\n";
            }
        }
        FreeMibTable(pTable);
    }

    return { neighbors, ERROR_SUCCESS };
}
