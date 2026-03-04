# CMakeList.txt : CMake project for Implant_v01
# cmake_minimum_required(VERSION 3.16) - trying for native PCH, aka pre compiled headers, for a speedup
cmake_minimum_required (VERSION 3.16)


project ("Implant_v01")

# ==========================================
# 1. Output Directory
# ==========================================
# This ensures the .exe ends up in the /output folder inside the container
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "/output")

# ==========================================
# 2. Source Files
# ==========================================

# Core sources
set(SOURCES
    "Implant_v01.cpp"
    "Implant_v01.h"
    "core/settings.h"
    "protocols/json/json.h"
    "data/msgpack/msgpack.cpp"
    "data/msgpack/msgpack.h"
    "data/transforms/transforms.cpp"
    "data/transforms/transforms.h"
    "tests/test.cpp"
    "tests/test.h"
    "protocols/base64/base64.cpp"
    "protocols/base64/base64.h"
    "comms/comms.cpp"
    "core/c2.h"
    "core/c2.cpp"
    "core/commandtree.cpp"
    "core/commandtree.h"
    "modules/cd.cpp" 
    "modules/cd.h" 
    "modules/strategy.cpp" 
    "modules/ls.cpp" 
    "modules/files.cpp" 
    "modules/files.h" 
    "data/structs.h"  
    "systems/memstore.h"
    "modules/metadata.cpp" 
    "modules/metadata.h"
    "modules/bof.cpp"
    "modules/bof.h"
    "libs/bof_launcher_api.h"
)
add_executable(Implant_v01 ${SOURCES} "modules/discover.cpp" "modules/discover.h" "comms/transport.h" )

target_precompile_headers(Implant_v01 PRIVATE
    <string>
    <vector>
    <map>
    <windows.h>
    "protocols/json/json.h"
    "data/msgpack/msgpack.h"
)
# ==========================================
# External Libraries (BofRunner)
# ==========================================
add_library(BofRunner STATIC IMPORTED)
set_target_properties(BofRunner PROPERTIES
    IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/libs/bof_launcher_win_x64.lib"
    # This tells CMake where the .h file is located
    INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/libs"
    # trying out unity builds, tldr, puts everything into one file, then compiles, so the compiler doesn't have to 
    # constantly read files. May cause name collisions with global vars.
    UNITY_BUILD ON
)
# ==========================================
# 3. Target Platform Logic (Windows)
# ==========================================
# tells windows.h and winsock2 to stop FUCKING fighting constantly (among other things)
add_compile_definitions(WIN32_LEAN_AND_MEAN)

if(WIN32)
    # Both MSVC and MinGW (Cross-compile) enter here
    
    # Add Windows-specific sources
    target_sources(Implant_v01 PRIVATE 
        "protocols/http_wininet/http.cpp"
        "protocols/http_wininet/http.h"
    )

target_link_libraries(Implant_v01 PRIVATE 
        BofRunner 
        wininet
        iphlpapi
        ws2_32
        crypt32
        ntdll
    )

    # MSVC Specific (Native Windows Build)
    if(MSVC)
        # Enable Hot Reload
        if (POLICY CMP0141)
            cmake_policy(SET CMP0141 NEW)
            set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT "$<IF:$<AND:$<C_COMPILER_ID:MSVC>,$<CXX_COMPILER_ID:MSVC>>,$<$<CONFIG:Debug,RelWithDebInfo>:EditAndContinue>,$<$<CONFIG:Debug,RelWithDebInfo>:ProgramDatabase>>")
        endif()

        # Force static runtime (/MT)
        foreach(flag_var
            CMAKE_C_FLAGS CMAKE_C_FLAGS_DEBUG CMAKE_C_FLAGS_RELEASE
            CMAKE_CXX_FLAGS CMAKE_CXX_FLAGS_DEBUG CMAKE_CXX_FLAGS_RELEASE)
            string(REPLACE "/MD" "/MT" ${flag_var} "${${flag_var}}")
        endforeach()
        
    # MinGW Specific (Cross-Compile on Linux)
    elseif(MINGW)
        # 1. Static Linking
        # Ensures libgcc/libstdc++ are built in, so you don't need DLLs on the target
        target_link_options(Implant_v01 PRIVATE 
            -static 
            -static-libgcc 
            -static-libstdc++
            # trying out LLD(LLVM linker)
            -fuse-ld=lld
        )
        
        # 2. Link System Libraries
        # MinGW needs explicit linking for WinINet and Winsock
        #target_link_libraries(Implant_v01 PRIVATE 
        #    wininet 
        #    ws2_32 
        #    crypt32
        #    BofRunner
        #)

        # set some stuff for optimizations
        set(CMAKE_CXX_FLAGS_RELEASE "-Os")
        set(CMAKE_C_FLAGS_RELEASE "-Os")

        # strip 
        set(CMAKE_EXE_LINKER_FLAGS "-s")

        # dead code elim
        # this might knock out those extra funcs in comms... needs testing. 
        #add_compile_options(-ffunction-sections -fdata-sections)
        #add_link_options(-Wl,--gc-sections)

        # notes, can switch to non-iostream/non-std libs for even smaller stuff if I need to. 

    endif()

endif()

# ==========================================
# 4. Standard Config
# ==========================================
if (CMAKE_VERSION VERSION_GREATER 3.12)
    set_property(TARGET Implant_v01 PROPERTY CXX_STANDARD 23)
endif()