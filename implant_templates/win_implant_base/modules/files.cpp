#include <string>
#include <vector>
#include "data/structs.h"
#include "defense/winapi.h"

/**
 * @brief Gets a file from the OS, and returns the content to the caller
 * @param std::string file_path: The path of the file. Ex: C:\Temp\myfile.txt
 * @return ModuleResult. data=file contents, windows_error_code=Any windows error codes if error occured, else 0.
*/
ModuleResult get_file(std::string file_path) {
	//https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew
	
	//convert to w string cuz windows
	std::wstring w_file_path(file_path.begin(), file_path.end());

	//get file handle first
	HANDLE h_file = WinApi::CreateFileW(
		static_cast<LPCWSTR>(w_file_path.c_str()), //static cast cuz it's safer than just (LPCWSTR)
		GENERIC_READ, //only need to read file
		FILE_SHARE_READ, //let other processes read, my thoguhts are to not inhibit other processes/users
		NULL, //dw sec attibutes, optional
		OPEN_EXISTING, //opens file, if not exist, returns 2 (send back an err not found)
		FILE_ATTRIBUTE_NORMAL, //docs say this is most common.
		NULL // template file, don't need

	);
	if (h_file == INVALID_HANDLE_VALUE) {
		return { "Could not get a handle to the file", WinApi::GetLastError()};
	}

	//get file size cus the winapi is barbaric and wants you to tell it how much of the file to read. 
	//https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-large_integer-r1 - this is where quadpart comes from.
	LARGE_INTEGER size;
	if (!WinApi::GetFileSizeEx(h_file, &size)) {
		WinApi::CloseHandle(h_file);
		return { "Could not get size of file", WinApi::GetLastError() };
	}

	std::string file_contents_buffer;
	// resize to fit the string, size.QuadPart is the total bytes from GetFileSizeEx
	file_contents_buffer.resize(static_cast<size_t>(size.QuadPart));
	DWORD bytes_read = 0;
	DWORD bytes_to_read = static_cast<DWORD>(size.QuadPart);

	//https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile
	//then read from the file handle
	BOOL read_success = WinApi::ReadFile(
		h_file,
		&file_contents_buffer[0], //using &var[0] for a writeable pointer, //(LPVOID)file_contents_buffer.c_str(), old method is a const char*
		bytes_to_read,
		&bytes_read,
		NULL //lpoverlapped, if running on win7 for some reason, this can't be NULL, so this will likely fail. 
	);

	if (!read_success) {
		return { "File read failed", WinApi::GetLastError() };
	}

	//could do a comparison of bytes to read, vs bytes read, and error if not fully read. 

	WinApi::CloseHandle(h_file);
	//return contents as str. 
	return { file_contents_buffer, 0 };

}

/**
 * @brief Writes a file to the OS. 
 * @param std::vector<uint8_t> file_contents: The file bytes to write to the file. 
 * @param std::string file_path: The path of the file to write. Ex: C:\Temp\myfile.txt
 * @return ModuleResult. data: A message if successful, windows_error_code=Any windows error codes if error occured, else 0.
*/
ModuleResult put_file(std::vector<uint8_t> file_contents, std::string file_path) {
	//convert to w string cuz windows
	std::wstring w_file_path(file_path.begin(), file_path.end());

	HANDLE h_file = WinApi::CreateFileW(
		static_cast<LPCWSTR>(w_file_path.c_str()),//static cast cuz it's safer than just (LPCWSTR)
		GENERIC_WRITE, //might need read as well
		0, //Tell every other process to fuck off while we write. 
		NULL, //dw sec attibutes, optional
		CREATE_NEW, //Create new if not exist, CREATE_ALWAYS may be worth looking into as well
		FILE_ATTRIBUTE_NORMAL, //docs say this is most common.
		NULL // template file, don't need

	);
	if (h_file == INVALID_HANDLE_VALUE) {
		//int return_code = static_cast<DWORD>(GetLastError());
		return { "Invalid handle to file", WinApi::GetLastError()};
	}

	LPDWORD bytes_written = 0;

	BOOL write_file = WinApi::WriteFile(
		h_file,
		static_cast<LPCVOID>(file_contents.data()), //get pointer of array, then cast to LPCVOID
		static_cast<DWORD>(file_contents.size()),
		bytes_written,
		NULL //lpoverlapped, optional, not including

	);

	//check if bytes written != array.size, throw something/err. 

	WinApi::CloseHandle(h_file);
	//success
	return { "File written successfully", 0 };

}