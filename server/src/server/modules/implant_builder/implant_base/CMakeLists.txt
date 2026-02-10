# CMakeList.txt : CMake project for Implant_v01
cmake_minimum_required (VERSION 3.10)

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
    "systems/memtrack.cpp"
    "control/settings.h"
    "protocols/json/json.h"
    "data/msgpack/msgpack.cpp"
    "data/msgpack/msgpack.h"
    "data/transforms/transforms.cpp"
    "data/transforms/transforms.h"
    "tests/test.cpp"
    "tests/test.h"
    "protocols/base64/base64.cpp"
    "protocols/base64/base64.h"
    "lifecycle/comms.cpp"
    "control/c2.h"
    "control/c2.cpp"
    "control/commandtree.cpp"
    "control/commandtree.h"

)

add_executable (Implant_v01 ${SOURCES} "modules/cd.cpp" "modules/cd.h" "modules/strategy.cpp" "modules/ls.cpp")

# ==========================================
# 3. Target Platform Logic (Windows)
# ==========================================

if(WIN32)
    # Both MSVC and MinGW (Cross-compile) enter here
    
    # Add Windows-specific sources
    target_sources(Implant_v01 PRIVATE 
        "protocols/http_wininet/http.cpp"
        "protocols/http_wininet/http.h"
    )

    # --- MSVC Specific (Native Windows Build) ---
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
        
    # --- MinGW Specific (Cross-Compile on Linux) ---
    elseif(MINGW)
        # 1. Static Linking
        # Ensures libgcc/libstdc++ are built in, so you don't need DLLs on the target
        target_link_options(Implant_v01 PRIVATE 
            -static 
            -static-libgcc 
            -static-libstdc++
        )
        
        # 2. Link System Libraries
        # MinGW needs explicit linking for WinINet and Winsock
        target_link_libraries(Implant_v01 PRIVATE 
            wininet 
            ws2_32 
            crypt32
        )

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