import re

content = open('frontend/static/js/app.js', encoding='utf-8').read()
methods = re.findall(r'^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{', content, re.MULTILINE)
print("Methods in app.js:")
for method in methods:
    print("-", method)
