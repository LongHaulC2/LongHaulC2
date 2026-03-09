#pragma once
#include <iostream>

/*
Note, this folder is named _debug cuz apparently debug/debug.h is a real
c++ file name, and causes a collision lol

*/

/*
Debug printing.

To use, just:

#include "_debug/debug.h"

DEBUG_LOG("Status: " << status << " to port " << 9090);

and go flip on the debug in cmake:
option(ENABLE_IMPLANT_LOGS "Enable internal debug logging" ON)

*/
#ifdef IMPLANT_DEBUG_LOGS
    // In Debug mode: Print to console
    #define DEBUG_LOG(x) std::cout << "[+] " << x << std::endl
#else
    // In Release mode: The preprocessor replaces this with nothing
    #define DEBUG_LOG(x) ((void)0)
#endif