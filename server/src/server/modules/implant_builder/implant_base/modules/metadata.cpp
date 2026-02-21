
#include <string>
#include <map>
#include <vector>
#include "../data/structs.h"
#include "metadata.h"
#include <lmcons.h> // Contains UNLEN (Maximum username length)
#include <filesystem>

//placeholder, move me to a diff file later, that has the ability to get this data
void populate_metadata(std::map<std::string, std::string>& metadata) {
    // Hardcoded placeholders as requested
    metadata["external_ip"] = "1.2.3.4";        // TODO: Fetch real external IP
	metadata["internal_ip"] = get_ip_address().data;   // TODO: Fetch real internal IP	
	metadata["user"] = get_current_user().data;
	metadata["system_hostname"] = get_computer_name().data;
	metadata["process"] = get_current_process_name().data;   // TODO: Get current process name
	metadata["pid"] = get_current_process_pid().data;
	metadata["arch"] = "x64";// TODO: Check system architecture

	//placeholders for dev
	//metadata["subnet_cidr"] = "10.0.0.0/24";// placehodler
	//maybe gw mac as well. can probably get via arp stuff

}


/**
 * @brief Get current user
 * @return ModuleResult. data: The current username, windows_error_code=Any windows error codes if error occured, else 0 (ERROR_SUCCESS).
*/
ModuleResult get_current_user() {
	// UNLEN is usually 256. We add 1 for the terminating null character.
	wchar_t buffer[UNLEN + 1];
	DWORD size = UNLEN + 1;

	// GetUserNameW returns non-zero on success
	if (GetUserNameW(buffer, &size)) {
		// use filesystem::path to handle the Wide to Narrow conversion safely
		// old method ofstd::string username_buffer(w_username_buffer.begin(), w_username_buffer.end()); could result in char corruption
		std::filesystem::path converter(buffer);
		return { converter.string(), ERROR_SUCCESS };
	}

	//on fail return blank
	return { "", GetLastError() };
}

ModuleResult get_computer_name() {
	// MAX_COMPUTERNAME_LENGTH is15, netbios limit
	wchar_t buffer[MAX_COMPUTERNAME_LENGTH + 1];
	DWORD size = MAX_COMPUTERNAME_LENGTH + 1;

	if (GetComputerNameW(buffer, &size)) {
		// use filesystem::path to handle the Wide to Narrow conversion safely
		// old method of std::string computer_name_buffer(w_computer_name_buffer.begin(), w_computer_name_buffer.end()); could result in char corruption
		std::filesystem::path converter(buffer);
		return { converter.string(), ERROR_SUCCESS };
	}

	return { "", GetLastError() };
}

ModuleResult get_current_process_name() {
	// 32767 is the approx max length for "\\?\" extended paths.
	std::vector<wchar_t> buffer(32767);

	DWORD length = GetModuleFileNameW(NULL, &buffer[0], buffer.size());

	if (length == 0) {
		return { "", GetLastError() };
	}

	// Check if buffer was too small
	if (length == buffer.size()) {
		return { "", ERROR_INSUFFICIENT_BUFFER };
	}

	// Convert Wide String (wchar_t) to std::string (UTF-8)
	// Can do this with std::filesystem
	try {
		std::filesystem::path myPath(&buffer[0]);
		return { myPath.string(), ERROR_SUCCESS };
	}
	catch (...) {
		return { "", ERROR_INVALID_DATA };
	}
}

ModuleResult get_current_process_pid() {
	std::vector<wchar_t> buffer(32767);

	DWORD pid = GetCurrentProcessId();


	if (pid == 0) {
		return { "", GetLastError() };
	}

	std::string s_pid = std::to_string(pid);
	return { s_pid, ERROR_SUCCESS };
}


#include <iostream>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <iphlpapi.h>
#include "../protocols/json/json.h"
#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "ws2_32.lib")

ModuleResult get_ip_address() {
    return { "0.1.3.4", ERROR_SUCCESS };
    ULONG flags = GAA_FLAG_INCLUDE_PREFIX | GAA_FLAG_INCLUDE_GATEWAYS;
    ULONG family = AF_INET; // IPv4 only
    ULONG bufferSize = 15000;

    PIP_ADAPTER_ADDRESSES adapters = (IP_ADAPTER_ADDRESSES*)malloc(bufferSize);
    if (adapters == nullptr) {
        return { nlohmann::json::object(), ERROR_NOT_ENOUGH_MEMORY };
    }

    DWORD dwRetVal = GetAdaptersAddresses(family, flags, NULL, adapters, &bufferSize);

    if (dwRetVal == ERROR_BUFFER_OVERFLOW) {
        free(adapters);
        adapters = (IP_ADAPTER_ADDRESSES*)malloc(bufferSize);
        dwRetVal = GetAdaptersAddresses(family, flags, NULL, adapters, &bufferSize);
    }

    nlohmann::json network_dict = nlohmann::json::object();

    if (dwRetVal == NO_ERROR) {
        for (PIP_ADAPTER_ADDRESSES adapter = adapters; adapter != NULL; adapter = adapter->Next) {

            // Skip disconnected and loopback
            if (adapter->OperStatus != IfOperStatusUp || adapter->IfType == IF_TYPE_SOFTWARE_LOOPBACK) {
                continue;
            }

            // 1. Format the MAC Address
            char macBuf[32] = { 0 };
            if (adapter->PhysicalAddressLength == 6) {
                snprintf(macBuf, sizeof(macBuf), "%02X-%02X-%02X-%02X-%02X-%02X",
                    adapter->PhysicalAddress[0], adapter->PhysicalAddress[1],
                    adapter->PhysicalAddress[2], adapter->PhysicalAddress[3],
                    adapter->PhysicalAddress[4], adapter->PhysicalAddress[5]);
            }

            // 2. Find the Gateway (if one exists for this adapter)
            std::string gatewayStr = "";
            for (PIP_ADAPTER_GATEWAY_ADDRESS_LH ga = adapter->FirstGatewayAddress; ga != NULL; ga = ga->Next) {
                if (ga->Address.lpSockaddr->sa_family == AF_INET) {
                    char gwIp[INET_ADDRSTRLEN];
                    sockaddr_in* gw_ipv4 = (sockaddr_in*)ga->Address.lpSockaddr;
                    inet_ntop(AF_INET, &gw_ipv4->sin_addr, gwIp, sizeof(gwIp));
                    gatewayStr = gwIp;
                    break; // Just grab the first IPv4 gateway
                }
            }

            // 3. Iterate through Unicast IPs and populate the dictionary
            for (PIP_ADAPTER_UNICAST_ADDRESS ua = adapter->FirstUnicastAddress; ua != NULL; ua = ua->Next) {
                if (ua->Address.lpSockaddr->sa_family == AF_INET) {
                    char ipStr[INET_ADDRSTRLEN];
                    sockaddr_in* ipv4 = (sockaddr_in*)ua->Address.lpSockaddr;
                    inet_ntop(AF_INET, &ipv4->sin_addr, ipStr, sizeof(ipStr));

                    // Add to dictionary with the IP as the key
                    network_dict[ipStr] = {
                        {"mac", macBuf},
                        {"gateway", gatewayStr},
                        {"cidr", ua->OnLinkPrefixLength}
                    };
                }
            }
        }
    }

    free(adapters);

    if (network_dict.empty() && dwRetVal == NO_ERROR) {
        return { nlohmann::json::object(), ERROR_NOT_FOUND };
    }

    // Return the json object directly into your new ModuleResult struct
    std::cout << "IP IS STRING TEMP PLACEHODLER" << std::endl;
    return { network_dict.dump(), dwRetVal};
}