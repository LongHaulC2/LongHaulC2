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
#include <netioapi.h> // Explicitly include this for Table2
#include <stdio.h>
#include <iostream>

#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "ws2_32.lib")

#include "../protocols/json/json.h"
#include "../data/structs.h"

//idea, name this "neighbor discovery" or something, for each enightbor, addd it to a map of ipand mac,and send back in data. 
// this allows for better parsing/neighbor discovery/a consistent return so the server knows how to handle it, and pass to neo4j.
ModuleResult passive_arp_discovery() {
    //https://learn.microsoft.com/en-us/windows/win32/api/netioapi/ns-netioapi-mib_ipnet_row2
    PMIB_IPNET_TABLE2 pTable = nullptr;

    // Swapped std::string for a JSON array
    nlohmann::json output = nlohmann::json::array();

    if (GetIpNetTable2(AF_UNSPEC, &pTable) == NO_ERROR) {
        for (ULONG i = 0; i < pTable->NumEntries; i++) {
            MIB_IPNET_ROW2 row = pTable->Table[i];

            // ONLY show entries that are confirmed reachable
            if (row.State == NlnsReachable) {
                wchar_t ipStr[64];
                InetNtopW(row.Address.si_family, &row.Address.Ipv4.sin_addr, ipStr, 64);

                //if (row.IsRouter) {
                //    printf("[GATEWAY] ");
                //}

                std::wstring w_string_ip(ipStr);
                std::string string_ip(w_string_ip.begin(), w_string_ip.end());

                // Formatting the MAC address
                char macBuf[32];
                snprintf(macBuf, sizeof(macBuf), "%02X-%02X-%02X-%02X-%02X-%02X",
                    row.PhysicalAddress[0], row.PhysicalAddress[1],
                    row.PhysicalAddress[2], row.PhysicalAddress[3],
                    row.PhysicalAddress[4], row.PhysicalAddress[5]);

                // Create the structured object for this neighbor
                nlohmann::json neighbor;
                neighbor["ip"] = string_ip;
                neighbor["mac"] = macBuf;

                output.push_back(neighbor);
            }
        }
        FreeMibTable(pTable);
    }

    return { output , ERROR_SUCCESS };
}