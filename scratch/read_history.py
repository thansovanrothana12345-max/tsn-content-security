import json
import os

log_path = r"C:\Users\USER\.gemini\antigravity-ide\brain\3385a5d8-9541-4d99-a071-d3a593c28a6c\.system_generated\logs\transcript.jsonl"
if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get("type") == "USER_INPUT" or data.get("source") == "USER_EXPLICIT":
                    print(f"Step {data.get('step_index')}: {data.get('content')}\n{'-'*50}")
            except Exception as e:
                pass
else:
    print("Log file not found.")
