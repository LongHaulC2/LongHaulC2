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

#include "protocols/json/json.h"
#include "data/structs.h"
#include "defense/winapi.h"
#include "_debug/debug.h"

//idea, name this "neighbor discovery" or something, for each enightbor, addd it to a map of ipand mac,and send back in data. 
// this allows for better parsing/neighbor discovery/a consistent return so the server knows how to handle it, and pass to neo4j.

//upate: arp alone was hard to work with, so now there's a hostname returned as well. 
//ideally, this will result in a NIC in the gui, and a host that it connects to via this info
ModuleResult passive_arp_discovery() {
    PMIB_IPNET_TABLE2 pTable = nullptr;
    nlohmann::json output = nlohmann::json::array();

    if (WinApi::GetIpNetTable2(AF_UNSPEC, &pTable) == NO_ERROR) {
        for (ULONG i = 0; i < pTable->NumEntries; i++) {
            MIB_IPNET_ROW2 row = pTable->Table[i];

            // Filter for Reachable only to avoid stale entries
            //fuuuuck that full send with all. I'd rather have more data than less.
            //could also put an arg in for this
            if (row.State == NlnsReachable || row.State == NlnsStale || row.State == NlnsDelay) {
                wchar_t ipStr[64];
                WinApi::InetNtopW(row.Address.si_family, &row.Address.Ipv4.sin_addr, ipStr, 64);

                // DNS Resolution Logic ---
                wchar_t hostName[NI_MAXHOST];
                std::string string_host = "";

                // NI_NAMEREQD: Only returns a name if one is found (prevents returning the IP as the name)
                // NI_NOFQDN: Returns only the hostname part for local hosts
                if (WinApi::GetNameInfoW((struct sockaddr*)&row.Address, sizeof(row.Address),
                    hostName, NI_MAXHOST, NULL, 0, NI_NAMEREQD | NI_NOFQDN) == 0) {
                    std::wstring w_host(hostName);
                    string_host = std::string(w_host.begin(), w_host.end());
                }
                // ---------------------------------

                std::wstring w_string_ip(ipStr);
                std::string string_ip(w_string_ip.begin(), w_string_ip.end());

                char macBuf[32];
                snprintf(macBuf, sizeof(macBuf), "%02X-%02X-%02X-%02X-%02X-%02X",
                    row.PhysicalAddress[0], row.PhysicalAddress[1],
                    row.PhysicalAddress[2], row.PhysicalAddress[3],
                    row.PhysicalAddress[4], row.PhysicalAddress[5]);

                nlohmann::json neighbor;
                neighbor["ip"] = string_ip;
                neighbor["mac"] = macBuf;
                neighbor["hostname"] = string_host; // Will be empty string if not found

                output.push_back(neighbor);
            }
        }
        WinApi::FreeMibTable(pTable);
    }

    return { output, ERROR_SUCCESS };
}