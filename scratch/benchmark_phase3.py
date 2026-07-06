import sys
import os
import time
import numpy as np
import tracemalloc

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.fingerprint import calculate_dhash, compare_fingerprints

def benchmark_dhash():
    print("--- Visual dHash Benchmark ---")
    # Simulate a 1080p frame (1920x1080 grayscale)
    img = np.random.randint(0, 255, (1080, 1920), dtype=np.uint8)
    
    # Warmup
    calculate_dhash(img)
    
    iterations = 200
    t0 = time.time()
    for _ in range(iterations):
        calculate_dhash(img)
    t1 = time.time()
    
    avg_latency_ms = ((t1 - t0) / iterations) * 1000
    print(f"Avg dHash Latency: {avg_latency_ms:.4f} ms per frame (Limit: <= 5.0 ms)")
    assert avg_latency_ms <= 5.0, f"dHash latency exceeded threshold: {avg_latency_ms} ms"
    print("OK: dHash performance benchmark passed.")
    return avg_latency_ms

def benchmark_similarity_matching():
    print("\n--- Sliding Window Similarity Matcher Benchmark ---")
    # Simulate fingerprint records of a 10-minute video (600 frames at 1 fps = 600 hashes)
    # and a 2-minute leak video (120 frames)
    fp1_fingerprint = [{"offset": float(i), "hash": f"{i:016x}"[-16:]} for i in range(600)]
    fp2_fingerprint = [{"offset": float(i), "hash": f"{(i+50):016x}"[-16:]} for i in range(120)]
    
    fp1_data = {
        "duration": 600.0,
        "fingerprint": fp1_fingerprint,
        "audio_peaks": [{"offset": float(i), "frequency": i % 200} for i in range(100)],
        "ocr_text": "sample text video",
        "logo_metadata": [],
        "metadata": {
            "codec_properties": {"width": 1920, "height": 1080, "duration": 600.0}
        }
    }
    
    fp2_data = {
        "duration": 120.0,
        "fingerprint": fp2_fingerprint,
        "audio_peaks": [{"offset": float(i), "frequency": (i+50) % 200} for i in range(20)],
        "ocr_text": "sample leak video text",
        "logo_metadata": [],
        "metadata": {
            "codec_properties": {"width": 1280, "height": 720, "duration": 120.0}
        }
    }
    
    # Warmup
    compare_fingerprints(fp1_data, fp2_data)
    
    iterations = 50
    tracemalloc.start()
    t0 = time.time()
    for _ in range(iterations):
        score, details = compare_fingerprints(fp1_data, fp2_data)
    t1 = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    avg_latency_ms = ((t1 - t0) / iterations) * 1000
    peak_mb = peak / (1024 * 1024)
    
    print(f"Avg Match Latency: {avg_latency_ms:.2f} ms (Target sliding alignment speedup check)")
    print(f"Peak Memory Overhead: {peak_mb:.4f} MB (Limit: <= 15.0 MB)")
    
    assert peak_mb <= 15.0, f"Memory limit exceeded: {peak_mb} MB"
    assert details["best_match_offset_sec"] == 50.0, f"Incorrect offset match: {details['best_match_offset_sec']}"
    print("OK: Similarity matching benchmark passed and offset bug successfully resolved.")
    return avg_latency_ms, peak_mb

if __name__ == "__main__":
    try:
        benchmark_dhash()
        benchmark_similarity_matching()
        print("\nALL PERFORMANCE BENCHMARKS PASSED SUCCESSFULLY! OK.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nBENCHMARK FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING BENCHMARKS: {e}", file=sys.stderr)
        sys.exit(1)
