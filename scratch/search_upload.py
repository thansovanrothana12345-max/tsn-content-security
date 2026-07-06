import os

for root, dirs, files in os.walk("backend"):
    for f in files:
        if f.endswith(".py"):
            filepath = os.path.join(root, f)
            content = open(filepath, encoding="utf-8").read()
            if "upload" in content or "file" in content:
                print(f"File {filepath} contains upload/file")
                for line in content.splitlines():
                    if "@router.post" in line or "@router.get" in line:
                        print("  ", line)
