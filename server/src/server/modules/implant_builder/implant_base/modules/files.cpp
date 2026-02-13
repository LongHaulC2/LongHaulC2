#include <string>
#include <vector>
#include <windows.h>

std::string get_file(std::string file_path) {
	//https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew
	
	//convert to w string cuz windows
	std::wstring w_file_path(file_path.begin(), file_path.end());

	//get file handle first
	HANDLE h_file = CreateFileW(
		(LPCWSTR)w_file_path.c_str(),
		GENERIC_READ, //only need to read file
		FILE_SHARE_READ, //let other processes read, my thoguhts are to not inhibit other processes/users
		NULL, //dw sec attibutes, optional
		OPEN_EXISTING, //opens file, if not exist, returns 2 (send back an err not found)
		FILE_ATTRIBUTE_NORMAL, //docs say this is most common.
		NULL // template file, don't need

	);
	if (!h_file) {
		return "";
	}

	//get file size cus the winapi is barbaric and wants you to tell it how much of the file to read. 
	//https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-large_integer-r1 - this is where quadpart comes from.
	LARGE_INTEGER size;
	if (!GetFileSizeEx(h_file, &size)) {
		CloseHandle(h_file);
		return "";
	}

	std::string file_contents_buffer;
	// resize to fit the string, size.QuadPart is the total bytes from GetFileSizeEx
	file_contents_buffer.resize(static_cast<size_t>(size.QuadPart));
	DWORD bytes_read = 0;
	DWORD bytes_to_read = static_cast<DWORD>(size.QuadPart);

	//https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile
	//then read from the file handle
	BOOL read_success = ReadFile(
		h_file,
		&file_contents_buffer[0], //using &var[0] for a writeable pointer, //(LPVOID)file_contents_buffer.c_str(), old method is a const char*
		bytes_to_read,
		&bytes_read,
		NULL //lpoverlapped, if running on win7 for some reason, this can't be NULL, so this will likely fail. 
	);

	if (!read_success) {
		return "";
	}

	//could do a comparison of bytes to read, vs bytes read, and error if not fully read. 

	//return contents as str. 
	return file_contents_buffer;

}