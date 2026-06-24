#include <windows.h>
#include <iostream>
//https://learn.microsoft.com/en-us/windows/win32/ipc/pipe-reference


/*
Notes, for child pipe, can either do one of the following to make sure our parent can write/read to it:

1. world readable/no auth: Easy, but sus

2. Domain users: Easierish, computer accounts/SYSTEM work, breaks on non-domain joined

3. allow SID of user/box to only read/write that pipe: Not ideal, but stealthy. Cannot switch chained beacons, UNLESS sid is added. 


*/
int child_pipe() {
//HANDLE CreateNamedPipeW(
//	[in]           LPCWSTR               lpName,
//	[in]           DWORD                 dwOpenMode,
//	[in]           DWORD                 dwPipeMode,
//	[in]           DWORD                 nMaxInstances,
//	[in]           DWORD                 nOutBufferSize,
//	[in]           DWORD                 nInBufferSize,
//	[in]           DWORD                 nDefaultTimeOut,
//	[in, optional] LPSECURITY_ATTRIBUTES lpSecurityAttributes
//);

	std::wstring wstr_pipe_inbox = L"\\\\.\\pipe\\inbox";

	//https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-createnamedpipew
	HANDLE h_inbox_pipe = CreateNamedPipeW(
		wstr_pipe_inbox.c_str(),      // pipe name
		PIPE_ACCESS_INBOUND,           // INBOX, so let external write to it, but only we can read
		PIPE_TYPE_MESSAGE |           // message type pipe, creates a queue basically
		PIPE_READMODE_MESSAGE |		  // read as message as well.
		PIPE_WAIT |					  // blocking mode - use this instead of nowait and poll
		PIPE_ACCEPT_REMOTE_CLIENTS,   // and accept remote conns to this             
		1,                            // max instances of inbox
		4096,                         // out buffer size - can boost later, probably gets into a chunking discussion
		4096,                         // in buffer size - max in, again chunking discussion/boost as needed.
		0,                            // default timeout - MS of how long to wait, 0 == 50 ms
		NULL                          // security descriptor, may be needed for remote conn
	);

	if (h_inbox_pipe == INVALID_HANDLE_VALUE) {
		std::cout << "Error: " << GetLastError() << std::endl;
		return 1;
	}
	std::cout << "Status: " << GetLastError() << std::endl;


	std::wstring wstr_pipe_outbox = L"\\\\.\\pipe\\outbox";

	//https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-createnamedpipew
	HANDLE h_outbox_pipe = CreateNamedPipeW(
		wstr_pipe_outbox.c_str(),      // pipe name
		PIPE_ACCESS_OUTBOUND,           // OUTBOX, so let external read, but only we can write
		PIPE_TYPE_MESSAGE |           // message type pipe, creates a queue basically
		PIPE_READMODE_MESSAGE |		  // read as message as well.
		PIPE_WAIT |					  // blocking mode - use this instead of nowait and poll
		PIPE_ACCEPT_REMOTE_CLIENTS,   // and accept remote conns to this             
		1,                            // max instances of inbox
		4096,                         // out buffer size - can boost later, probably gets into a chunking discussion
		4096,                         // in buffer size - max in, again chunking discussion/boost as needed.
		0,                            // default timeout - MS of how long to wait, 0 == 50 ms
		NULL                          // security descriptor, may be needed for remote conn
	);

	if (h_outbox_pipe == INVALID_HANDLE_VALUE) {
		std::cout << "Error: " << GetLastError() << std::endl;
		return 1;
	}
	std::cout << "Status: " << GetLastError() << std::endl;


	return 0;


}

int main() {
	std::cout << "Parent Process" << std::endl;
	//HANDLE CreateNamedPipeW(
	//	[in]           LPCWSTR               lpName,
	//	[in]           DWORD                 dwOpenMode,
	//	[in]           DWORD                 dwPipeMode,
	//	[in]           DWORD                 nMaxInstances,
	//	[in]           DWORD                 nOutBufferSize,
	//	[in]           DWORD                 nInBufferSize,
	//	[in]           DWORD                 nDefaultTimeOut,
	//	[in, optional] LPSECURITY_ATTRIBUTES lpSecurityAttributes
	//);
	//HANDLE parent_pipe

	//ookay idea:

	//1. Parent connect to pipe of child (do a loop over here or just run child first for testing?)

	//2. Parent writes to inbox pipe

	//...other execution stuff...
	//...child writes to outbox pipe...

	//3. parent checks outbox pipe for data. if data, enqueue in response list and yeet back to server

	std::cout << "Child Process" << std::endl;
	child_pipe();


}