# gradescope_utils/runner/json_runner_with_locks.py
from datetime import datetime, timezone
import unittest
from gradescope_utils.autograder_utils.json_test_runner import JSONTestRunner

class JSONTestRunnerWithLocks(JSONTestRunner):
    """
    Extends JSONTestRunner:
    - Tests with _gs_available_from in the future are not run.
    - They are excluded from the total max score by default.
    - Optionally included in output with hidden visibility & a message.
    """

    def __init__(self, *args, include_locked_in_output=False,
                 locked_message_template="This test unlocks on {iso}.",
                 strip_test_prefix=False,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.include_locked_in_output = include_locked_in_output
        self.locked_message_template = locked_message_template
        self.strip_test_prefix = strip_test_prefix

    @staticmethod
    def _now_utc():
        # Allows override via env var for local testing/replays
        import os
        override = os.getenv("GS_NOW_UTC")  # e.g., "2025-10-01T09:00:00Z"
        if override:
            if override.endswith("Z"):
                override = override.replace("Z", "+00:00")
            return datetime.fromisoformat(override).astimezone(timezone.utc)
        return datetime.now(timezone.utc)

    def _clean_test_name(self, name):
        """Clean up test name by optionally removing 'Test' prefix"""
        if not self.strip_test_prefix:
            return name
            
        # Remove "Test" from the beginning of the name if present
        import re
        # Pattern to match "Test" at start, optionally followed by numbers/dots
        # Examples: "Test01. Something" -> "01. Something", "Test Something" -> "Something"  
        pattern = r'^Test\s*(\d+\.?\s*)?'
        cleaned = re.sub(pattern, r'\1', name)
        return cleaned.strip()

    def _flatten_tests(self, suite):
        """Yield test cases from a possibly nested suite."""
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                yield from self._flatten_tests(item)
            else:
                yield item

    def _is_locked(self, test):
        fn = getattr(test, test._testMethodName, None)
        unlock_dt = getattr(fn, "__gs_available_from__", None)
        if unlock_dt is None:
            return False, None
        now = self._now_utc()
        return now < unlock_dt, unlock_dt

    def run(self, test):
        # Split tests into runnable vs locked
        runnable_suite = unittest.TestSuite()
        locked_tests = []
        for t in self._flatten_tests(test):
            locked, unlock_dt = self._is_locked(t)
            if locked:
                locked_tests.append((t, unlock_dt))
            else:
                runnable_suite.addTest(t)

        # Set up post-processor BEFORE calling parent run
        prev_post = self.post_processor

        def post_proc(payload):
            # payload: {'tests': [...], 'score': float, 'max_score': float, ...}
            # Calculate the correct max_score from runnable tests only
            def _weight_from_test(t):
                # Same logic the utils use: test.__weight__ or default 1.0
                method = getattr(t, t._testMethodName, None)
                return getattr(method, "__weight__", 1.0)

            # Calculate max_score from the tests that actually ran
            total_max_score = 0.0
            for test_result in payload.get("tests", []):
                total_max_score += test_result.get("max_score", 0.0)
            payload["max_score"] = total_max_score

            if self.include_locked_in_output:
                for t, unlock_dt in locked_tests:
                    # Use the same naming logic as the base JSONTestRunner
                    doc_first_line = t.shortDescription()
                    if self.descriptions and doc_first_line:
                        name = doc_first_line
                    else:
                        name = str(t)
                    
                    # Clean up the test name if requested
                    name = self._clean_test_name(name)
                    
                    # Use any per-test visibility if present; otherwise make visible
                    method = getattr(t, t._testMethodName, None)
                    vis = getattr(method, "__visibility__", "visible")
                    reason = getattr(method, "__gs_available_from_reason__", None)
                    msg = self.locked_message_template.format(iso=unlock_dt.isoformat())
                    if reason:
                        msg = f"{msg}\nReason: {reason}"
                    payload.setdefault("tests", []).append({
                        "name": name,
                        "score": 0,
                        "max_score": 0,  # critically make it zero so it doesn't affect totals
                        "output": msg,
                        "visibility": vis,
                    })

            if prev_post:
                payload = prev_post(payload)
            return payload

        # Set the post-processor before running
        self.post_processor = post_proc
        
        # Run only the runnable tests using the parent implementation
        result = super().run(runnable_suite)
        
        # Restore the original post-processor
        self.post_processor = prev_post
        
        return result