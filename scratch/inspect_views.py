import re

content = open('frontend/static/index.html', encoding='utf-8').read()

views = [
    "view-dashboard",
    "view-cases",
    "view-verification",
    "view-library",
    "view-scanner",
    "view-reports",
    "view-security",
    "view-settings"
]

for view in views:
    print(f"\n=========================================\nVIEW: {view}\n=========================================")
    # Extract the block starting with <section id="view" and ending with </section>
    match = re.search(r'<section\s+id=["\']' + view + r'["\'].*?</section>', content, re.DOTALL)
    if match:
        snippet = match.group(0)
        # print first 15 lines and last 5 lines of the snippet
        lines = snippet.split('\n')
        if len(lines) > 30:
            print("\n".join(lines[:20]))
            print("...")
            print("\n".join(lines[-10:]))
        else:
            print(snippet)
    else:
        print("NOT FOUND")
