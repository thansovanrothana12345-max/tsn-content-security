import sys
import os
import threading
import time
import socket
import traceback

# Prevent any redirection
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app as fastapi_app
from backend.worker import worker_loop
import uvicorn

# We will record thread exception here
thread_exception = None

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def run_server(port):
    global thread_exception
    try:
        print(f"Uvicorn thread started, port={port}")
        uvicorn.run(fastapi_app, host="127.0.0.1", port=port, log_level="warning")
    except Exception as e:
        thread_exception = e
        print(f"Exception in uvicorn thread: {e}")
        traceback.print_exc()

def wait_for_port(port, host="127.0.0.1", timeout=5.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect((host, port))
                return True
        except socket.error:
            time.sleep(0.1)
    return False

def main():
    global thread_exception
    port = find_free_port()
    print(f"Allocated port: {port}")
    
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()
    
    worker_thread = threading.Thread(target=worker_loop, daemon=True)
    worker_thread.start()
    
    print("Waiting for port to open...")
    if not wait_for_port(port):
        print("Error: Backend server failed to start in time.", file=sys.stderr)
        if thread_exception:
            print(f"Captured exception: {thread_exception}", file=sys.stderr)
        else:
            print("No exception was captured from the server thread. Thread is alive:", server_thread.is_alive(), file=sys.stderr)
        sys.exit(1)
        
    print(f"Backend listening on http://127.0.0.1:{port}")
    sys.exit(0)

if __name__ == "__main__":
    main()
