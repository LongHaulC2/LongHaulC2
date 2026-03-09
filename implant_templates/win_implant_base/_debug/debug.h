#pragma once

#ifdef IMPLANT_DEBUG_LOGS

#include <sstream>
#include <string>

void internal_log_write(const std::string& message);

#define DEBUG_LOG(x) \
    do { \
        std::ostringstream _oss; \
        _oss << "[+] " << x; \
        internal_log_write(_oss.str()); \
    } while(0)

#else
    // If not in debug mode, compile to nothing
    #define DEBUG_LOG(x) do {} while(0)
#endif