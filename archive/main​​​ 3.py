import sys
import os

# Redirect stdout/stderr to devnull in gui mode to prevent write attribute crashes
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import threading
import time
import socket
import uvicorn
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

# Import the FastAPI application and worker loop
from backend.app import app as fastapi_app
from backend.worker import worker_loop
from backend.config import Config

class CustomWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[JS CONSOLE] {message} (Line {lineNumber}, Source: {sourceID})")

def find_free_port():
    """Finds an unused TCP port to run our local server on."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def run_server(port):
    """Runs the FastAPI server inside a background thread."""
    uvicorn.run(fastapi_app, host="127.0.0.1", port=port, log_level="warning")

def wait_for_port(port, host="127.0.0.1", timeout=5.0):
    """Retries connecting to the port until it is open."""
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

class MainWindow(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.setWindowTitle("Copyright Security — AI-Powered Copyright Protection & Evidence Management")
        self.resize(1366, 850)
        
        # Setup Web View
        self.web_view = QWebEngineView()
        self.custom_page = CustomWebEnginePage(self.web_view)
        self.web_view.setPage(self.custom_page)
        
        # Connect to render termination to monitor crash status
        self.web_view.page().renderProcessTerminated.connect(
            lambda status, code: print(f"Error: Chromium render process terminated. Status: {status}, Exit Code: {code}", file=sys.stderr)
        )
        
        self.web_view.setUrl(QUrl(url))
        self.setCentralWidget(self.web_view)
       

def main():
    # 1. Determine port (use Config.PORT if set, otherwise find a free port)
    port = Config.PORT if Config.PORT > 0 else find_free_port()
    
    # 2. Spawn uvicorn backend server in daemon thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()
    
    # 2b. Spawn background queue worker in daemon thread
    worker_thread = threading.Thread(target=worker_loop, daemon=True)
    worker_thread.start()
    
    # 3. Wait for backend startup
    if not wait_for_port(port):
        print("Error: Backend server failed to start in time.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Backend listening on http://127.0.0.1:{port}")
    
    # 4. Start PySide6 Native desktop app
    qt_app = QApplication(sys.argv)
    window = MainWindow(f"http://127.0.0.1:{port}/")
    window.show()
    
    # Run loop
    sys.exit(qt_app.exec())

if __name__ == "__main__":
    main()
