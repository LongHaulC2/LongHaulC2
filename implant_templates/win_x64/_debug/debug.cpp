#include "debug.h"

#ifdef IMPLANT_DEBUG_LOGS

#include <iostream>
#include <fstream>
#include <mutex>

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

static DebugLogger global_debug_logger("implant_debug.log");

void internal_log_write(const std::string& message) {
    std::cout << message << std::endl;
    global_debug_logger.write(message);
}

#endif