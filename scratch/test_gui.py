import sys
import os
import threading
import time
import socket
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtNetwork import QNetworkProxy

# Configure test parameters
USE_NO_SANDBOX = "--no-sandbox" in sys.argv
USE_NO_PROXY = "--no-proxy" in sys.argv

if USE_NO_SANDBOX:
    print("Setting Chromium flag: --no-sandbox")
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"

if USE_NO_PROXY:
    print("Setting Application Proxy: NoProxy")
    QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.NoProxy))

import sys
import os

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app as fastapi_app
import uvicorn

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

class CustomWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[JS CONSOLE] {message} (Line {lineNumber}, Source: {sourceID})")

from backend.worker import worker_loop

def run_server(port):
    uvicorn.run(fastapi_app, host="127.0.0.1", port=port, log_level="warning")

def wait_for_port(port, timeout=5.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("127.0.0.1", port))
                return True
        except socket.error:
            time.sleep(0.1)
    return False

def main():
    port = find_free_port()
    t = threading.Thread(target=run_server, args=(port,), daemon=True)
    t.start()
    
    # Spawn background queue worker in daemon thread
    worker_thread = threading.Thread(target=worker_loop, daemon=True)
    worker_thread.start()
    
    if not wait_for_port(port):
        print("Server failed to start")
        sys.exit(1)
        
    print(f"Server is listening on http://127.0.0.1:{port}")
    
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.resize(800, 600)
    
    web = QWebEngineView()
    custom_page = CustomWebEnginePage(web)
    web.setPage(custom_page)
    
    web.loadStarted.connect(lambda: print("[DEBUG] Load started..."))
    web.loadProgress.connect(lambda p: print(f"[DEBUG] Load progress: {p}%"))
    web.loadFinished.connect(lambda ok: print(f"[DEBUG] Load finished. Status: {ok}"))
    web.page().renderProcessTerminated.connect(
        lambda status, code: print(f"[DEBUG ERROR] Render terminated. Status: {status}, Code: {code}")
    )
    
    web.setUrl(QUrl(f"http://127.0.0.1:{port}/"))
    window.setCentralWidget(web)
    window.show()
    
    # Auto-close after 8 seconds so the test finishes cleanly
    def auto_close():
        time.sleep(8)
        print("Test duration ended, closing window.")
        app.quit()
        
    threading.Thread(target=auto_close, daemon=True).start()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
