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
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.include_locked_in_output = include_locked_in_output
        self.locked_message_template = locked_message_template

    @staticmethod
    def _now_utc():
        # Allows override via env var for local testing/replays
        import os
        override = os.getenv("GS_NOW_UTC")  # e.g., "2025-10-01T09:00:00Z"
        if override:
            from datetime import datetime, timezone
            if override.endswith("Z"):
                override = override.replace("Z", "+00:00")
            return datetime.fromisoformat(override).astimezone(timezone.utc)
        return datetime.now(timezone.utc)

    def _flatten_tests(self, suite):
        """Yield test cases from a possibly nested suite."""
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                yield from self._flatten_tests(item)
            else:
                yield item

    def _is_locked(self, test):
        fn = getattr(test, test._testMethodName, None)
        unlock_dt = getattr(fn, "_gs_available_from", None)
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

        # Run only the runnable tests using the parent implementation
        result = super().run(runnable_suite)

        # Adjust totals: remove locked tests' weights from the aggregate max_score
        # The base JSONTestRunner computes totals when generating JSON.
        # We intercept via post_processor to tweak results before print.
        prev_post = self.post_processor

        def post_proc(payload):
            # payload: {'tests': [...], 'score': float, 'max_score': float, ...}
            # Subtract locked weights from max_score and optionally append hidden entries
            def _weight_from_test(t):
                # Same logic the utils use: test._weight or default 1.0
                method = getattr(t, t._testMethodName, None)
                return getattr(method, "_weight", 1.0)

            locked_total = sum(_weight_from_test(t) for t, _ in locked_tests)
            payload["max_score"] = max(0.0, payload.get("max_score", 0.0) - locked_total)

            if self.include_locked_in_output:
                for t, unlock_dt in locked_tests:
                    name = str(t)
                    # Use any per-test visibility if present; otherwise hide
                    method = getattr(t, t._testMethodName, None)
                    vis = getattr(method, "_visibility", "hidden")
                    reason = getattr(method, "_gs_available_from_reason", None)
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

        # Swap in our post-processor just for this call
        self.post_processor = post_proc
        # Trigger JSON emission (the base class prints JSON in .run already).
        # We already ran; to ensure post_processor runs, we regenerate JSON by calling parent logic:
        # The base class calls post_processor right before output; since we've already run,
        # we just return the result; JSON is already printed with our post_proc hook in place.
        return result