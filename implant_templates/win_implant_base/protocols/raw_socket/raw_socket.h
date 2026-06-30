#pragma once
// winsock2 must come before any windows.h include to avoid WinSock v1 conflicts.
// transport.h defines WIN32_LEAN_AND_MEAN before including windows.h, which prevents
// windows.h from pulling in winsock.h (v1) — so including winsock2.h here is safe.
#include <winsock2.h>
#include <ws2tcpip.h>
#include <string>
#include <vector>

#pragma comment(lib, "ws2_32.lib")

// ============================================================================
// Internal helpers (not for direct use outside this header)
// ============================================================================
namespace RawSocket {

inline bool _init() {
    static bool done = false;
    if (!done) {
        WSADATA wsa = {};
        done = (WSAStartup(MAKEWORD(2, 2), &wsa) == 0);
    }
    return done;
}

// Convert wide string host to narrow ASCII for socket API calls
inline std::string _narrow(const std::wstring& wide) {
    if (wide.empty())
        return {};
    int sz = WideCharToMultiByte(CP_ACP, 0, wide.data(), static_cast<int>(wide.size()), nullptr, 0, nullptr, nullptr);
    std::string out(sz, '\0');
    WideCharToMultiByte(CP_ACP, 0, wide.data(), static_cast<int>(wide.size()), out.data(), sz, nullptr, nullptr);
    return out;
}

} // namespace RawSocket

// ============================================================================
// Public API
// ============================================================================

// TCP: connect → send all request bytes → shutdown send → read until server closes → close
inline bool RAW_TCP_SEND_RECV(const std::wstring& host, int port, const std::vector<uint8_t>& request,
                               std::vector<uint8_t>& response) {
    if (!RawSocket::_init())
        return false;

    std::string host_str = RawSocket::_narrow(host);
    std::string port_str = std::to_string(port);

    addrinfo hints = {};
    addrinfo* result = nullptr;
    hints.ai_family   = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    if (getaddrinfo(host_str.c_str(), port_str.c_str(), &hints, &result) != 0)
        return false;

    SOCKET sock = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (sock == INVALID_SOCKET) {
        freeaddrinfo(result);
        return false;
    }

    if (connect(sock, result->ai_addr, static_cast<int>(result->ai_addrlen)) == SOCKET_ERROR) {
        closesocket(sock);
        freeaddrinfo(result);
        return false;
    }
    freeaddrinfo(result);

    // Send request bytes then signal end-of-send so server knows when to respond
    if (send(sock, reinterpret_cast<const char*>(request.data()), static_cast<int>(request.size()), 0) == SOCKET_ERROR) {
        closesocket(sock);
        return false;
    }
    shutdown(sock, SD_SEND);

    // Read response until server closes connection
    char buf[4096];
    int n;
    while ((n = recv(sock, buf, sizeof(buf), 0)) > 0) {
        response.insert(response.end(), buf, buf + n);
    }

    closesocket(sock);
    return true;
}

// UDP: sendto → recvfrom (with 5-second timeout)
inline bool RAW_UDP_SEND_RECV(const std::wstring& host, int port, const std::vector<uint8_t>& request,
                               std::vector<uint8_t>& response) {
    if (!RawSocket::_init())
        return false;

    std::string host_str = RawSocket::_narrow(host);
    std::string port_str = std::to_string(port);

    addrinfo hints = {};
    addrinfo* result = nullptr;
    hints.ai_family   = AF_INET;
    hints.ai_socktype = SOCK_DGRAM;
    hints.ai_protocol = IPPROTO_UDP;

    if (getaddrinfo(host_str.c_str(), port_str.c_str(), &hints, &result) != 0)
        return false;

    SOCKET sock = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (sock == INVALID_SOCKET) {
        freeaddrinfo(result);
        return false;
    }

    sendto(sock, reinterpret_cast<const char*>(request.data()), static_cast<int>(request.size()), 0, result->ai_addr,
           static_cast<int>(result->ai_addrlen));
    freeaddrinfo(result);

    // 5-second receive timeout — no response means the server had no tasks (204 equivalent)
    DWORD timeout_ms = 5000;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));

    char buf[65536];
    sockaddr_in from  = {};
    int         fromlen = sizeof(from);
    int n = recvfrom(sock, buf, sizeof(buf), 0, reinterpret_cast<sockaddr*>(&from), &fromlen);
    if (n > 0) {
        response.assign(buf, buf + n);
    }

    closesocket(sock);
    return true;
}
