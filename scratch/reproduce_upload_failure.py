import sys
import os
import time
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

class AutomationPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[BROWSER CONSOLE] {message} (Line {lineNumber}, Source: {sourceID})")

def run_automation():
    app = QApplication(sys.argv)
    
    view = QWebEngineView()
    page = AutomationPage(view)
    view.setPage(page)
    
    # Track steps
    step = 0
    
    def execute_next_step():
        nonlocal step
        step += 1
        
        if step == 1:
            # Step 1: Login
            js_login = """
            console.log("Automation Step 1: Logging in...");
            const emailInput = document.getElementById('login-email-input');
            const passwordInput = document.getElementById('login-password-input');
            if (emailInput && passwordInput) {
                emailInput.value = 'admin@example.com';
                passwordInput.value = 'AdminPassword123';
                document.getElementById('login-form').dispatchEvent(new Event('submit'));
                console.log("Login form submitted");
            } else {
                console.log("No login screen active or bypass already completed");
            }
            """
            page.runJavaScript(js_login)
            QTimer.singleShot(3000, execute_next_step)
            
        elif step == 2:
            # Step 2: Select case & navigate to evidence tab & simulate upload
            js_upload = """
            console.log("Automation Step 2: Simulating evidence upload...");
            
            // 1. Ensure a case is active
            const caseSelect = document.getElementById('global-case-select');
            if (caseSelect && !caseSelect.value && caseSelect.options.length > 1) {
                caseSelect.value = caseSelect.options[1].value;
                caseSelect.dispatchEvent(new Event('change'));
                console.log("Selected case folder: " + caseSelect.value);
            }
            
            // 2. Open cases view and details tab
            if (window.app) {
                window.app.switchView('cases');
                window.app.switchDetailsTab('evidence');
                console.log("Switched to cases and evidence tabs");
            }
            
            // 3. Inject mock JPG file to file input
            setTimeout(() => {
                const fileInput = document.getElementById('evidence-file-input');
                if (fileInput) {
                    console.log("Found file input, injecting mock JPG file...");
                    const file = new File(["dummy jpeg content"], "test_evidence.JPG", { type: "image/jpeg" });
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    fileInput.files = dt.files;
                    fileInput.dispatchEvent(new Event('change'));
                    console.log("Mock file change event dispatched");
                } else {
                    console.log("Could not find file input element!");
                }
            }, 1000);
            """
            page.runJavaScript(js_upload)
            QTimer.singleShot(4000, execute_next_step)
            
        elif step == 3:
            print("Automation complete. Exiting...")
            app.quit()
            
    view.setUrl(QUrl("http://127.0.0.1:8000/"))
    view.resize(1366, 850)
    view.show()
    
    # Wait 3 seconds for initial load, then start steps
    QTimer.singleShot(3000, execute_next_step)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    run_automation()
