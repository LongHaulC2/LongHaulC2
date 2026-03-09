#pragma once

#include <chrono>
#include <random>
#include <iomanip>
#include <sstream>
#include <cstdint>
#include <string>

namespace uuid7 {
    inline std::string generate() {
        // Get current timestamp in milliseconds (48 bits needed)
        auto now = std::chrono::system_clock::now();
        uint64_t ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()).count();

        //  Initialize random number generator
        std::random_device rd;
        std::mt19937_64 gen(rd());
        std::uniform_int_distribution<uint64_t> dist;

        // Generate random bits
        uint64_t rand_a = dist(gen) & 0x0FFF;             // 12 bits of randomness
        uint64_t rand_b = dist(gen) & 0x3FFFFFFFFFFFFFFF; // 62 bits of randomness

        // Assemble the two 64-bit halves
        // High 64 bits: 48-bit timestamp | 4-bit version (0x7) | 12-bit rand_a
        uint64_t high = (ms << 16) | 0x7000 | rand_a;

        // Low 64 bits: 2-bit variant (0x8) | 62-bit rand_b
        uint64_t low = 0x8000000000000000ULL | rand_b;

        // Format to standard 8-4-4-4-12 string representation
        std::stringstream ss;
        ss << std::hex << std::setfill('0')
            << std::setw(8) << (high >> 32) << '-'
            << std::setw(4) << ((high >> 16) & 0xFFFF) << '-'
            << std::setw(4) << (high & 0xFFFF) << '-'
            << std::setw(4) << (low >> 48) << '-'
            << std::setw(12) << (low & 0xFFFFFFFFFFFFULL);

        return ss.str();
    }
}