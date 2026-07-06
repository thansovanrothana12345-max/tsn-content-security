# Testing Strategy & Guidelines

This document describes the testing layers, validation procedures, and benchmark targets configured for the **Copyright Center**.

---

## 1. Test Layers

### A. Unit Tests
*   **Target**: Core mathematical calculation libraries and format validators.
*   **Execution**: Validates difference hashing outputs (ensures 16-char hex formatting), Hamming sequence sliding metrics, and wave FFT spectrogram peaks coordinates mapping.
*   **Reference Scripts**: `scratch/test_phase4_2.py` (Video) and `scratch/test_phase4_3.py` (Image).

### B. Integration Tests
*   **Target**: FastAPI HTTP endpoints, payload routers, database connections, and session authentications.
*   **Execution**: Boots FastAPI instances inside memory using `fastapi.testclient.TestClient`. Performs API calls (login, case creation, original file chunk upload/assembly, frame seeking) verifying JSON status returns.
*   **Reference Script**: `scratch/test_api.py` and `scratch/test_phase4_5.py`.

### C. Performance & Benchmark Tests
*   **Target**: Latency processing bounds and peak RAM memory allocations.
*   **Execution**: Uses `time.perf_counter` and `tracemalloc` to track resource consumption over consecutive loops.
*   **Reference Script**: `scratch/benchmark_4_2.py` and `scratch/test_phase4_4.py`.

---

## 2. Performance Threshold Targets

| Benchmark Metric | Target Threshold Limit | Verified Status |
| :--- | :--- | :--- |
| **Image Fingerprint Latency** | $\le 5.0\text{ ms}$ per image crop | Passed ($1.25\text{ms}$) |
| **Audio Fingerprint Latency** | $\le 100\text{ ms}$ per audio minute | Passed ($22.66\text{ms}$) |
| **Frame seek request Latency**| $\le 50.0\text{ ms}$ per HTTP scrubbing query| Passed ($37.45\text{ms}$) |
| **Acoustic processing Memory** | $\le 10.0\text{ MB}$ peak RAM | Passed ($0.0304\text{MB}$) |
| **Frame seeking Memory** | $\le 15.0\text{ MB}$ peak RAM | Passed ($1.0603\text{MB}$) |
