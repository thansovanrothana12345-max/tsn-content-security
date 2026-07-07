import sys
import os
import importlib.util

# Set up stdout/stderr so they are not None and not redirected
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

# Adjust Python path to allow backend imports
sys.path.insert(0, r"F:\TOOL\TSN Content Security")
print("SYS PATH:", sys.path)
dir_files = os.listdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
main3_filename = None
for f in dir_files:
    if f.startswith("main") and "3.py" in f:
        main3_filename = f
        break

if not main3_filename:
    print("Could not find main 3.py file!")
    sys.exit(1)

main3_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), main3_filename)
print(f"Found main 3.py at: {repr(main3_path)}")

# Load the module dynamically
spec = importlib.util.spec_from_file_location("main3", main3_path)
main3 = importlib.util.module_from_spec(spec)
sys.modules["main3"] = main3
spec.loader.exec_module(main3)

print("Starting main3.main()...")
try:
    main3.main()
except Exception as e:
    print(f"Exception during main3.main(): {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
