# Developer Contribution Guide

Welcome to the **Copyright Center** codebase. Follow this guide to prepare branches, execute tests, and submit sub-phase updates.

---

## 1. Development Workflow
Every sub-phase implementation must follow this sequence:
1.  **Technical Specification**: Design architecture and database updates first.
2.  **Implementation**: Write clean, parameterized Python code.
3.  **Unit & Integration Tests**: Verify logic using local scripts in the `scratch/` directory.
4.  **Performance Verification**: Trace RAM memory footprint and execution latency.
5.  **Technical Report**: Document test coverage and benchmarks.

---

## 2. Coding Guidelines
*   **Queries Parameterization**: Never concatenate variables inside SQL statements; always use `?` placeholders.
*   **Resource Releases**: Ensure file streams (`cv2.VideoCapture` pointers, wave file readers) are released in `finally` blocks.
*   **Path traversals check**: Use `os.path.abspath` and match path prefixes against configured directories to block file boundary exploits.
*   **Linting**: Follow PEP 8 guidelines.

---

## 3. Standard Tests Protocol
Before checking in work, run the test scripts:
```bash
python scratch/test_phase4_2.py
python scratch/test_phase4_3.py
python scratch/test_phase4_4.py
python scratch/test_phase4_5.py
```
Assert that all print logs return `OK:` and exits with code 0.
