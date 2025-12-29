# potential listener pattern w multiprocessing & start/stop comms.
# note,  could pass a dict or json (may need to be a str for ipc?) as an instruction set for listener
# listener would retrieve all data from redis, and write *back* to redis (and then that data is parsed by the server to mysql

import multiprocessing
import time


# Simulate a connection listener
def listener(listener_id, control_queue):
    print(f"Listener {listener_id} started...")

    try:
        while True:
            if not control_queue.empty():
                command = control_queue.get_nowait()
                if command == "STOP":
                    print(f"Listener {listener_id} received STOP command.")
                    break
                elif command == "PAUSE":
                    print(f"Listener {listener_id} paused.")
                    time.sleep(1)  # Simulate pause
            time.sleep(0.1)  # Simulate waiting for connections
            print(f"Listener {listener_id} listening for connections...")
    except KeyboardInterrupt:
        print(f"Listener {listener_id} stopping...")


# Start listeners and set up control queue
def start_listeners(num_listeners, control_queue):
    processes = []

    for i in range(num_listeners):
        listener_process = multiprocessing.Process(
            target=listener, args=(i, control_queue)
        )
        listener_process.daemon = True
        listener_process.start()
        processes.append(listener_process)

    return processes


# Main program with control functionality
if __name__ == "__main__":
    control_queue = multiprocessing.Queue()  # Queue for IPC
    num_listeners = 5  # Example: Start 5 listeners
    processes = start_listeners(num_listeners, control_queue)

    # Simulate some control commands
    time.sleep(5)
    control_queue.put("PAUSE")  # Pause all listeners for a moment
    time.sleep(5)
    control_queue.put("STOP")  # Stop all listeners

    # Keep main program running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Main program stopping...")
        for process in processes:
            process.terminate()  # Terminate listener processes cleanly
