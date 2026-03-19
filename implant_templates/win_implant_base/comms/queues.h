#pragma once

// dedicated file for response queue
#include <queue>
#include <mutex>
#include "protocols/json/json.h"
#include <iostream>
#include "_debug/debug.h"

/*
Hi!

This is where the queues live for get/post actions.

They are thread safe, and self lock themselves with mutexes.

Please don't lock them manually unless you know what you are doing/need to,
otherwise you can run into weird deadlocks/double locks

*/

/**
 * @namespace GetQueue
 * @brief Holds functions related to interacting with the GetQueue
 */
namespace GetQueue {
    //inline cuz this is a .h, and functinos are called from multiple files
    inline std::queue<nlohmann::json> get_queue;
    inline std::mutex get_queue_mutex;


    //a dedicated store task here would be cool
    /**
     * @brief Pushes a task into the Get queue. The GetQueue is an array of all inbound tasks
     * 
     * @param task_result A nlohmann::json object, which is the task result
     */
    inline void push(nlohmann::json task_result) {
        std::lock_guard<std::mutex> lock(get_queue_mutex);
        get_queue.push(task_result);

        //debug inbound
        DEBUG_LOG("queued task for get_queue back to server:");
        DEBUG_LOG(task_result.dump(4));
    }

    /**
     * @brief Drains all items from the queue
     * 
     * @return nlohmann::json::array An array of tasks, from the GetQueue
     */
    inline nlohmann::json drain_queue() {
        std::lock_guard<std::mutex> lock(get_queue_mutex);

        nlohmann::json results = nlohmann::json::array();

        while (!get_queue.empty()) {
            results.push_back(get_queue.front());
            get_queue.pop();
        }

        // debug outbound
        DEBUG_LOG("drained get_queue results to send to server:");
        DEBUG_LOG(results.dump(4));

        return results;
    }
}

/**
 * @namespace PostQueue
 * @brief Holds functions related to interacting with the PostQueue
 */
namespace PostQueue {
    //inline cuz this is a .h, and functinos are called from multiple files
    inline std::queue<nlohmann::json> post_queue;
    inline std::mutex mutex;

    //a dedicated store task here would be cool

    /**
     * @brief Pushes a task into the PostQueue. The PostQueue is an array
    of all tasks to be POSTed back to the server (or next up the chain)
     * 
     * @param task_result 
     */
    inline void push(nlohmann::json task_result) {
        std::lock_guard<std::mutex> lock(mutex);
        post_queue.push(task_result);

        //debug inbound
        DEBUG_LOG("queued task for response:");
        DEBUG_LOG(task_result.dump(4));
    }
}