/**
 * @file winapi_wrapper.h
 * @brief A centralized wrapper around Windows API functions.
 * * This wrapper allows for easy modification of the underlying Windows API resolution 
 * mechanism (e.g., using lazy_importer) without altering the core logic of the program. 
 * Functions are inlined to avoid multiple definition issues while acting as a 
 * direct substitute for native API calls.
 *
 * @note Every WinAPI function used in the project must be declared here.
 * @see https://malapi.io/ for identifying required DLLs for specific functions.
 */

#pragma once

#include "lazy_importer.hpp"
#include <winsock2.h>
#include <ws2tcpip.h>
#include <iphlpapi.h>
#include "_debug/debug.h"
/**
 * @namespace WinApi
 * @brief Encapsulates wrapped Windows API functions to manage resolution and prevent naming collisions.
 *
 * The standard Windows API functions within this namespace are direct 1:1 wrappers. 
 * For parameter and return type details on these functions, refer to the official Microsoft documentation.
 */
namespace WinApi {

    /**
     * @brief Ensures a specified module is loaded into memory.
     * * Prevents lazy_importer from crashing by checking if a module is already in the PEB,
     * and calling LoadLibraryA if it is not found.
     * * @param moduleName The name of the module (DLL) to verify and potentially load.
     */
    inline void EnsureModuleLoaded(LPCSTR moduleName) {
        DEBUG_LOG("[WinApi::EnsureModuleLoaded] Checking if module is loaded: " + std::string(moduleName));        
        if (!LI_FN(GetModuleHandleA)(moduleName)) {
            DEBUG_LOG("[WinApi::EnsureModuleLoaded] Module not found. Calling LoadLibraryA on: " + std::string(moduleName));
            LI_FN(LoadLibraryA)(moduleName);
        }
        DEBUG_LOG("[WinApi::EnsureModuleLoaded] Already loaded!: " + std::string(moduleName));
    }

    inline void Sleep(DWORD ms) {
        DEBUG_LOG("[WinApi::Sleep] Calling Sleep");
        LI_FN(Sleep)(ms);
    }

    inline BOOL SetCurrentDirectoryW(LPCWSTR lpPathName) {
        DEBUG_LOG("[WinApi::SetCurrentDirectoryW] Calling SetCurrentDirectoryW");
        return LI_FN(SetCurrentDirectoryW)(lpPathName);
    }

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

    inline DWORD GetLastError() {
        DEBUG_LOG("[WinApi::GetLastError] Calling GetLastError");
        return LI_FN(GetLastError)();
    }

    inline BOOL GetUserNameW(LPWSTR lpBuffer, LPDWORD pcbBuffer) {
        DEBUG_LOG("[WinApi::GetUserNameW] Calling GetUserNameW");
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

    inline BOOL DisconnectNamedPipe(HANDLE hNamedPipe) {
        DEBUG_LOG("[WinApi::DisconnectNamedPipe] Calling DisconnectNamedPipe");
        return LI_FN(DisconnectNamedPipe)(hNamedPipe);
    }

    inline PTP_WORK CreateThreadpoolWork(PTP_WORK_CALLBACK pfnwk, PVOID pv, PTP_CALLBACK_ENVIRON pcbe) {
        DEBUG_LOG("[WinApi::CreateThreadpoolWork] Calling CreateThreadpoolWork");
        return ::CreateThreadpoolWork(pfnwk, pv, pcbe);
    }

    inline VOID SubmitThreadpoolWork(PTP_WORK pwk) {
        DEBUG_LOG("[WinApi::SubmitThreadpoolWork] Calling SubmitThreadpoolWork");
        return ::SubmitThreadpoolWork(pwk);
    }

    inline VOID CloseThreadpoolWork(PTP_WORK pwk) {
        DEBUG_LOG("[WinApi::CloseThreadpoolWork] Calling CloseThreadpoolWork");
        return ::CloseThreadpoolWork(pwk);
    }

    inline HANDLE CreateEventW(LPSECURITY_ATTRIBUTES lpEventAttributes, BOOL bManualReset, BOOL bInitialState, LPCWSTR lpName) {
        DEBUG_LOG("[WinApi::CreateEventW] Calling CreateEventW");
        return ::CreateEventW(lpEventAttributes, bManualReset, bInitialState, lpName);
    }

    inline BOOL SetEvent(HANDLE hEvent) {
        DEBUG_LOG("[WinApi::SetEvent] Calling SetEvent");
        return ::SetEvent(hEvent);
    }

    inline DWORD WaitForSingleObject(HANDLE hHandle, DWORD dwMilliseconds) {
        DEBUG_LOG("[WinApi::WaitForSingleObject] Calling WaitForSingleObject");
        return ::WaitForSingleObject(hHandle, dwMilliseconds);
    }

    inline DWORD WaitForMultipleObjects(DWORD nCount, const HANDLE *lpHandles, BOOL bWaitAll, DWORD dwMilliseconds) {
        DEBUG_LOG("[WinApi::WaitForMultipleObjects] Calling WaitForMultipleObjects");
        return ::WaitForMultipleObjects(nCount, lpHandles, bWaitAll, dwMilliseconds);
    }

    inline BOOL CloseHandle(HANDLE hObject) {
        DEBUG_LOG("[WinApi::CloseHandle] Calling CloseHandle");
        return ::CloseHandle(hObject);
    }

    inline HANDLE CreateThread(LPSECURITY_ATTRIBUTES lpThreadAttributes, SIZE_T dwStackSize, LPTHREAD_START_ROUTINE lpStartAddress, LPVOID lpParameter, DWORD dwCreationFlags, LPDWORD lpThreadId) {
        DEBUG_LOG("[WinApi::CreateThread] Calling CreateThread");
        return LI_FN(CreateThread)(lpThreadAttributes, dwStackSize, lpStartAddress, lpParameter, dwCreationFlags, lpThreadId);
    }

    inline HANDLE CreateNamedPipeW(LPCWSTR lpName, DWORD dwOpenMode, DWORD dwPipeMode, DWORD nMaxInstances, DWORD nOutBufferSize, DWORD nInBufferSize, DWORD nDefaultTimeOut, LPSECURITY_ATTRIBUTES lpSecurityAttributes) {
        DEBUG_LOG("[WinApi::CreateNamedPipeW] Calling CreateNamedPipeW");
        return LI_FN(CreateNamedPipeW)(lpName, dwOpenMode, dwPipeMode, nMaxInstances, nOutBufferSize, nInBufferSize, nDefaultTimeOut, lpSecurityAttributes);
    }

    inline BOOL ConnectNamedPipe(HANDLE hNamedPipe, LPOVERLAPPED lpOverlapped) {
        DEBUG_LOG("[WinApi::ConnectNamedPipe] Calling ConnectNamedPipe");
        return LI_FN(ConnectNamedPipe)(hNamedPipe, lpOverlapped);
    }

    inline BOOL WaitNamedPipeW(LPCWSTR lpNamedPipeName, DWORD nTimeOut) {
        DEBUG_LOG("[WinApi::WaitNamedPipeW] Calling WaitNamedPipeW");
        return LI_FN(WaitNamedPipeW)(lpNamedPipeName, nTimeOut);
    }
}