import time
import sys
import os
import cv2
import numpy as np

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
from backend.fingerprint import calculate_dhash
from backend.services.cache import DetectionCache

def benchmark_dhash_speed():
    print("--- Benchmarking dHash Frame Generation ---")
    dummy_frame = np.random.randint(0, 256, (720, 1280), dtype=np.uint8)
    
    start_time = time.perf_counter()
    iterations = 5000
    for _ in range(iterations):
        calculate_dhash(dummy_frame)
    duration = time.perf_counter() - start_time
    
    if duration > 0:
        fps = iterations / duration
        print(f"Computed {iterations} dHash frames in {duration:.4f}s ({fps:.2f} frames/sec)")
    else:
        print(f"Computed {iterations} dHash frames near-instantaneously.")

def benchmark_cache_speed():
    print("\n--- Benchmarking Detection Cache Speeds ---")
    cache = DetectionCache(use_memory=True, use_db=True)
    cache.clear()
    
    key = "benchmark_key_123"
    value = '{"overall_similarity": 0.85, "confidence_score": 0.90, "confidence_level": "High"}'
    
    cache.set(key, value)
    
    # 1. Measure Memory Hit latency
    start_time = time.perf_counter()
    for _ in range(5000):
        cache.get(key)
    duration = time.perf_counter() - start_time
    print(f"Memory Cache Retrieve Latency: {duration*1000/5000:.6f} ms per hit")
    
    # Disable memory cache to measure DB Retrieve latency
    cache.use_memory = False
    start_time = time.perf_counter()
    for _ in range(100):
        cache.get(key)
    duration = time.perf_counter() - start_time
    print(f"Database Cache Retrieve Latency: {duration*1000/100:.6f} ms per hit")
    
    cache.clear()

if __name__ == "__main__":
    benchmark_dhash_speed()
    benchmark_cache_speed()
