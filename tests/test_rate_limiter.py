from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from API_Tools.rate_limiter import (
    SlidingWindowRateLimiter,
    acquire_provider_slot,
    configured_kimi_rpm,
    is_kimi_model,
)


class ProviderDetectionTests(unittest.TestCase):
    def test_kimi_keys_and_model_names_share_the_limited_provider(self):
        self.assertTrue(is_kimi_model("Kimi-k2.5", "kimi-k2.5"))
        self.assertTrue(is_kimi_model("Kimi-k2.5_think", "kimi-k2.5"))
        self.assertTrue(is_kimi_model("custom", "moonshot-v1-128k"))

    def test_non_kimi_models_are_not_limited(self):
        self.assertFalse(is_kimi_model("DeepSeek-V4-flash", "deepseek-v4-flash"))
        self.assertFalse(is_kimi_model("Qwen3-8b", "qwen3-8b"))

    def test_non_kimi_call_does_not_create_limiter_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "limits.sqlite3"
            with patch.dict("os.environ", {"SC2_RATE_LIMIT_DB": str(state)}):
                self.assertEqual(0.0, acquire_provider_slot("DeepSeek-V4-flash", "deepseek-v4-flash"))
            self.assertFalse(state.exists())

    def test_configuration_cannot_exceed_provider_ceiling(self):
        with patch.dict("os.environ", {"SC2_KIMI_RPM": "61"}):
            with self.assertRaises(ValueError):
                configured_kimi_rpm()


class SlidingWindowTests(unittest.TestCase):
    def test_separate_instances_share_one_window(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "limits.sqlite3"
            first = SlidingWindowRateLimiter(state, limit=2, window_seconds=0.15, bucket="kimi")
            second = SlidingWindowRateLimiter(state, limit=2, window_seconds=0.15, bucket="kimi")
            first.acquire()
            second.acquire()
            started = time.monotonic()
            second.acquire()
            self.assertGreaterEqual(time.monotonic() - started, 0.10)


if __name__ == "__main__":
    unittest.main()
