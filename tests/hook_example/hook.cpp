#include <windows.h>
#include <iostream>
#include <setjmp.h>

// Global buffer to hold the CPU state
jmp_buf jump_buffer;

//Funcs to call when hooked
void WINAPI ExitProcessFunc(UINT uExitCode) {
	printf("[*] ExitProcess called: Hook Successful!\n");
	longjmp(jump_buffer, 1);
}

void WINAPI TerminateProcessFunc(UINT uExitCode) {
	printf("[*] TerminateProcess called: Hook Successful!\n");
	//ExitThread(uExitCode);
	//instead of exiting, jump back to previous stuff
	longjmp(jump_buffer, 1);
}

void WINAPI TerminateThreadFunc(UINT uExitCode) {
	printf("[*] TerminateThread called: Hook Successful!\n");
	ExitThread(uExitCode);
	//instead of exiting, jump back to previous stuff
	longjmp(jump_buffer, 1);
}

void setup_exit_hook_ExitProcess() {
	//HMODULE kernel32 = GetModuleHandleA("kernel32.dll");
	////snag address of the real exit process
	//void* realExit = GetProcAddress(kernel32, "ExitThread");

	//HMODULE ntdll = GetModuleHandleA("ntdll.dll");
	//void* realExit = GetProcAddress(ntdll, "NtTerminateProcess");
	HMODULE k32 = GetModuleHandleA("kernel32.dll");
	void* realExit = GetProcAddress(k32, "ExitProcess");

	// Simple Trampoline Hook (x64)
	// MOV RAX, <Address of MyExitProcess>
	// JMP RAX
	uint8_t trampoline[] = {
		0x48, 0xB8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // MOV RAX, <ADDR>
		0xFF, 0xE0                                                  // JMP RAX
	};

	// Patch the address of our function into the trampoline
	//literally editing the function that's in our mem here to jump to our funcion
	uintptr_t hookAddr = (uintptr_t)&ExitProcessFunc;
	memcpy(&trampoline[2], &hookAddr, sizeof(hookAddr));

	// Write the hook onto the real ExitProcess
	DWORD oldProtect;
	VirtualProtect(realExit, sizeof(trampoline), PAGE_EXECUTE_READWRITE, &oldProtect);
	memcpy(realExit, trampoline, sizeof(trampoline));
	VirtualProtect(realExit, sizeof(trampoline), oldProtect, &oldProtect);

	//flush l1
	//FlushInstructionCache(GetCurrentProcess(), realExit, sizeof(trampoline));
}

void setup_exit_hook_NtTerminateProcess() {
	//HMODULE kernel32 = GetModuleHandleA("kernel32.dll");
	////snag address of the real exit process
	//void* realExit = GetProcAddress(kernel32, "ExitThread");

	//HMODULE ntdll = GetModuleHandleA("ntdll.dll");
	//void* realExit = GetProcAddress(ntdll, "NtTerminateProcess");
	HMODULE ntdll = GetModuleHandleA("ntdll.dll");
	void* realExit = GetProcAddress(ntdll, "NtTerminateProcess");

	// Simple Trampoline Hook (x64)
	// MOV RAX, <Address of MyExitProcess>
	// JMP RAX
	uint8_t trampoline[] = {
		0x48, 0xB8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // MOV RAX, <ADDR>
		0xFF, 0xE0                                                  // JMP RAX
	};

	// Patch the address of our function into the trampoline
	//literally editing the function that's in our mem here to jump to our funcion
	uintptr_t hookAddr = (uintptr_t)&TerminateProcessFunc;
	memcpy(&trampoline[2], &hookAddr, sizeof(hookAddr));

	// Write the hook onto the real ExitProcess
	DWORD oldProtect;
	VirtualProtect(realExit, sizeof(trampoline), PAGE_EXECUTE_READWRITE, &oldProtect);
	memcpy(realExit, trampoline, sizeof(trampoline));
	VirtualProtect(realExit, sizeof(trampoline), oldProtect, &oldProtect);

	//flush l1
	//FlushInstructionCache(GetCurrentProcess(), realExit, sizeof(trampoline));
}

void setup_exit_hook_NtTerminateThread() {
	HMODULE ntdll = GetModuleHandleA("ntdll.dll");
	void* realExit = GetProcAddress(ntdll, "NtTerminateThread");

	// Simple Trampoline Hook (x64)
	// MOV RAX, <Address of MyExitProcess>
	// JMP RAX
	uint8_t trampoline[] = {
		0x48, 0xB8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // MOV RAX, <ADDR>
		0xFF, 0xE0                                                  // JMP RAX
	};

	// Patch the address of our function into the trampoline
	//literally editing the function that's in our mem here to jump to our funcion
	uintptr_t hookAddr = (uintptr_t)&TerminateThreadFunc;
	memcpy(&trampoline[2], &hookAddr, sizeof(hookAddr));

	// Write the hook onto the real ExitProcess
	DWORD oldProtect;
	VirtualProtect(realExit, sizeof(trampoline), PAGE_EXECUTE_READWRITE, &oldProtect);
	memcpy(realExit, trampoline, sizeof(trampoline));
	VirtualProtect(realExit, sizeof(trampoline), oldProtect, &oldProtect);

	//flush l1
	//FlushInstructionCache(GetCurrentProcess(), realExit, sizeof(trampoline));
}

int main() {
	//print pid for tracking
	DWORD current_pid = GetCurrentProcessId();
	std::cout << "Current Process ID (PID): " << current_pid << std::endl;

	setup_exit_hook_ExitProcess();
	setup_exit_hook_NtTerminateProcess();
	setup_exit_hook_NtTerminateThread();

	// The Checkpoint
	// This saves the stack pointer (RSP) and instruction pointer (RIP).
	int jumpResult = setjmp(jump_buffer);

	//longjump jumps exactly back here

	if (jumpResult == 0) {
		// This runs FIRST.
		printf("[+] Checkpoint saved. Executing shellcode...\n");


		// Simulating calling a function that is hooked
		ExitProcess(0); 

	}
	else {
		// This runs AFTER longjmp is called.
		printf("[+] HA you can't exit.\n");
		printf("[+] You can now continue executing normal code.\n");
		//reset result to 0, so subsequent calls jump back to above the if/else tree
		jumpResult == 0;
		//sleep for 5 seocnds, then "exit"
		Sleep(5000);
		ExitProcess(0);

	}

	// Continue normal execution...
	std::cout << "[+] Program is still running normally." << std::endl;
	getchar();
	return 0;
}
