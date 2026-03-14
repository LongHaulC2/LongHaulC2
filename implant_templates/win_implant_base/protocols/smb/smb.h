#pragma once
#include <windows.h>
#include <vector>
#include "_debug/debug.h"


namespace SMB {
	DWORD read_pipe_dynamic(HANDLE h_pipe, std::vector<uint8_t>& out_buffer);

	//funcs for if we are the child
	namespace Child {
		//int register_pipe(HANDLE& h_inbox_pipe, HANDLE& h_outbox_pipe); //comms.h
		std::vector<uint8_t> read_from_pipe(HANDLE pipe, OVERLAPPED* ol);
		bool await_client_connection(HANDLE h_pipe, const std::string& pipe_name);
		std::vector<uint8_t> fetch_tasks(HANDLE h_inbox, HANDLE h_outbox, const std::vector<uint8_t>& get_request_payload);
		bool send_data(HANDLE h_outbox, const std::vector<uint8_t>& payload);
	}

	//funcs for if we are the parent
	namespace Parent {
		nlohmann::json cycle_child(HANDLE h_write, HANDLE h_read, const nlohmann::json& raw_task, bool expect_response);
	}
}
