
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

ModuleResult get_ip_address() {
	return { "someip", ERROR_SUCCESS };
}