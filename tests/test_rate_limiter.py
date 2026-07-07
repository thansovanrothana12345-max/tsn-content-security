import unittest
import sys
import os

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.config import Config
from backend.middleware.rate_limiter import RateLimiterMiddleware

class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.add_middleware(RateLimiterMiddleware)
        
        @self.app.get("/api/v1/auth/test")
        def auth_endpoint():
            return {"status": "ok"}
            
        self.client = TestClient(self.app)
        
        # Override config limits for tests
        Config.RATE_LIMIT_ENABLED = True
        Config.RATE_LIMIT_AUTH_COUNT = 3
        Config.RATE_LIMIT_AUTH_WINDOW = 5

    def test_rate_limiting_throttling(self):
        # First 3 requests should pass
        for _ in range(3):
            response = self.client.get("/api/v1/auth/test")
            self.assertEqual(response.status_code, 200)
            
        # 4th request should get rate limited (HTTP 429)
        response_throttled = self.client.get("/api/v1/auth/test")
        self.assertEqual(response_throttled.status_code, 429)
        self.assertEqual(response_throttled.json()["error"], "RATE_LIMIT_EXCEEDED")

if __name__ == "__main__":
    unittest.main()
