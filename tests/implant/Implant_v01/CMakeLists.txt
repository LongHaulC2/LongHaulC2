# CMakeList.txt : CMake project for Implant_v01, include source and define
# project specific logic here.
#
cmake_minimum_required (VERSION 3.10)

# Enable Hot Reload for MSVC compilers if supported.
if (POLICY CMP0141)
  cmake_policy(SET CMP0141 NEW)
  set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT "$<IF:$<AND:$<C_COMPILER_ID:MSVC>,$<CXX_COMPILER_ID:MSVC>>,$<$<CONFIG:Debug,RelWithDebInfo>:EditAndContinue>,$<$<CONFIG:Debug,RelWithDebInfo>:ProgramDatabase>>")
endif()

project ("Implant_v01")

# Add source to this project's executable.
add_executable (Implant_v01 "Implant_v01.cpp" "Implant_v01.h" "systems/memtrack.cpp" "protocols/http_wininet/http.cpp" "control/settings/settings.cpp" "protocols/http_wininet/http.h")

if (CMAKE_VERSION VERSION_GREATER 3.12)
  set_property(TARGET Implant_v01 PROPERTY CXX_STANDARD 20)
endif()

# TODO: Add tests and install targets if needed.
