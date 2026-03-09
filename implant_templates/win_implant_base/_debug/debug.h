#pragma once
#include <iostream>

#ifdef IMPLANT_DEBUG_LOGS

#include <fstream>
#include <mutex>
#include <string>
#include <sstream>

class DebugLogger {
private:
    std::ofstream file;
    std::mutex mtx;

public:
    DebugLogger(const std::string& filename) {
        file.open(filename, std::ios::app);
    }

    ~DebugLogger() {
        if (file.is_open()) {
            file.close();
        }
    }

    void write(const std::string& message) {
        std::lock_guard<std::mutex> lock(mtx);
        if (file.is_open()) {
            file << message << "\n";
            file.flush(); 
        }
    }
};

//create one instance of the class
// "inline" ensures we don't get "multiple definition" linker errors.
inline DebugLogger global_debug_logger("implant_debug.log");

#define DEBUG_LOG(x) \
    do { \
        std::ostringstream _oss; \
        _oss << "[+] " << x; \
        std::cout << _oss.str() << std::endl; \
        global_debug_logger.write(_oss.str()); \
    } while(0)

#else
    // if not in debug mode, this replaces the output with nothing
    #define DEBUG_LOG(x) ((void)0)
#endif