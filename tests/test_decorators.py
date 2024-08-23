import unittest
from gradescope_utils.autograder_utils.json_test_runner import JSONTestRunner
from gradescope_utils.autograder_utils.decorators import (
    weight,
    visibility,
    timeout,
    custom_output,
    leaderboard,
    partial_credit,
)
import time
import tempfile
import json


class TestDecorators(unittest.TestCase):

    @staticmethod
    def run_test_with_decorators(decorators, fn):
        class InnerTestCase(unittest.TestCase):
            def test_foo(self, *args, **kwargs):
                fn(*args, **kwargs)
                self.assertTrue(True)

        # Apply decorators
        for decorator in reversed(decorators):
            InnerTestCase.test_foo = decorator(InnerTestCase.test_foo)

        suite = unittest.TestLoader().loadTestsFromTestCase(InnerTestCase)

        with tempfile.TemporaryFile(mode="w+") as f:
            JSONTestRunner(visibility="visible", stream=f).run(suite)
            f.seek(0)
            results = json.load(f)

        return results

    def test_weight_passed(self):
        def assert_1_equals_1():
            assert 1 == 1, "WTF"

        results = TestDecorators.run_test_with_decorators(
            decorators=[weight(2)],
            fn=assert_1_equals_1,
        )

        self.assertEqual(results["tests"][0]["max_score"], 2)
        self.assertEqual(results["tests"][0]["score"], 2)
        self.assertEqual(results["tests"][0]["status"], "passed")

    def test_weight_failed(self):
        def assert_1_equals_0():
            assert 1 == 0, "Failure"

        results = TestDecorators.run_test_with_decorators(
            decorators=[weight(3)],
            fn=assert_1_equals_0,
        )

        self.assertEqual(results["tests"][0]["max_score"], 3)
        self.assertEqual(results["tests"][0]["score"], 0)
        self.assertEqual(results["tests"][0]["status"], "failed")

    def test_visibility_hidden(self):
        def assert_1_equals_1():
            assert 1 == 1, "WTF"

        results = TestDecorators.run_test_with_decorators(
            decorators=[visibility("hidden")],
            fn=assert_1_equals_1,
        )

        self.assertEqual(results["tests"][0]["visibility"], "hidden")
        self.assertEqual(results["tests"][0]["status"], "passed")

    def test_timeout_success(self):
        def assert_1_equals_1():
            assert 1 == 1, "WTF"

        results = TestDecorators.run_test_with_decorators(
            decorators=[timeout(1), weight(1)],
            fn=assert_1_equals_1,
        )

        self.assertEqual(results["tests"][0]["status"], "passed")
        self.assertEqual(results["tests"][0]["max_score"], 1)
        self.assertEqual(results["tests"][0]["score"], 1)

    def test_timeout_success_flip_order(self):
        def assert_1_equals_1():
            assert 1 == 1, "WTF"

        results = TestDecorators.run_test_with_decorators(
            decorators=[weight(1), timeout(1)],
            fn=assert_1_equals_1,
        )

        self.assertEqual(results["tests"][0]["status"], "passed")
        self.assertEqual(results["tests"][0]["max_score"], 1)
        self.assertEqual(results["tests"][0]["score"], 1)

    def test_timeout_failure(self):
        def delay_two_seconds():
            time.sleep(2)

        results = TestDecorators.run_test_with_decorators(
            decorators=[timeout(1), weight(1)],
            fn=delay_two_seconds,
        )

        self.assertEqual(results["tests"][0]["status"], "failed")
        self.assertEqual(results["tests"][0]["max_score"], 1)
        self.assertEqual(results["tests"][0]["score"], 0)

    def test_partial_credit_success(self):
        def wrapped(set_score=None):
            set_score(1.0)

        results = TestDecorators.run_test_with_decorators(
            decorators=[partial_credit(1.0)],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["max_score"], 1.0)
        self.assertEqual(results["tests"][0]["score"], 1.0)
        self.assertEqual(results["tests"][0]["status"], "passed")

    def test_partial_credit_failure(self):
        def wrapped(set_score=None):
            set_score(0.5)

        results = TestDecorators.run_test_with_decorators(
            decorators=[partial_credit(1.0)],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["max_score"], 1.0)
        self.assertEqual(results["tests"][0]["score"], 0.5)
        self.assertEqual(results["tests"][0]["status"], "failed")

    def test_partial_credit_timeout_stacking_passed_1(self):
        def wrapped(set_score=None):
            set_score(1.0)

        results = TestDecorators.run_test_with_decorators(
            decorators=[partial_credit(1.0), timeout(1)],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["max_score"], 1.0)
        self.assertEqual(results["tests"][0]["score"], 1.0)
        self.assertEqual(results["tests"][0]["status"], "passed")

    def test_partial_credit_timeout_stacking_passed_2(self):
        def wrapped(set_score=None):
            set_score(1.0)

        results = TestDecorators.run_test_with_decorators(
            decorators=[timeout(1), partial_credit(1.0)],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["max_score"], 1.0)
        self.assertEqual(results["tests"][0]["score"], 1.0)
        self.assertEqual(results["tests"][0]["status"], "passed")

    def test_partial_credit_timeout_stacking_failed_1(self):
        def wrapped(set_score=None):
            set_score(0.5)
            time.sleep(2)
            set_score(1.0)

        results = TestDecorators.run_test_with_decorators(
            decorators=[partial_credit(1.0), timeout(1)],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["max_score"], 1.0)
        self.assertEqual(results["tests"][0]["score"], 0.5)
        self.assertEqual(results["tests"][0]["status"], "failed")

    def test_partial_credit_timeout_stacking_failed_2(self):
        def wrapped(set_score=None):
            set_score(0.5)
            time.sleep(2)
            set_score(1.0)

        results = TestDecorators.run_test_with_decorators(
            decorators=[timeout(1), partial_credit(1.0)],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["max_score"], 1.0)
        self.assertEqual(results["tests"][0]["score"], 0.5)
        self.assertEqual(results["tests"][0]["status"], "failed")

    def test_leaderboard(self):
        def wrapped(set_leaderboard_value=None):
            set_leaderboard_value(42)

        results = TestDecorators.run_test_with_decorators(
            decorators=[leaderboard("score")],
            fn=wrapped,
        )

        self.assertEqual(results["leaderboard"][0]["name"], "score")
        self.assertEqual(results["leaderboard"][0]["value"], 42)

    def test_stacking_leaderboard_timeout_1(self):
        def wrapped(set_leaderboard_value=None):
            set_leaderboard_value(42)

        results = TestDecorators.run_test_with_decorators(
            decorators=[leaderboard("score"), timeout(1)],
            fn=wrapped,
        )

        self.assertEqual(results["leaderboard"][0]["name"], "score")
        self.assertEqual(results["leaderboard"][0]["value"], 42)

    def test_stacking_leaderboard_timeout_2(self):
        def wrapped(set_leaderboard_value=None):
            set_leaderboard_value(42)

        results = TestDecorators.run_test_with_decorators(
            decorators=[timeout(1), leaderboard("score")],
            fn=wrapped,
        )

        self.assertEqual(results["leaderboard"][0]["name"], "score")
        self.assertEqual(results["leaderboard"][0]["value"], 42)

    def test_stacking_leaderboard_timeout_failure(self):
        def wrapped(set_leaderboard_value=None):
            time.sleep(2)
            set_leaderboard_value(42)

        results = TestDecorators.run_test_with_decorators(
            decorators=[timeout(1), leaderboard("score")],
            fn=wrapped,
        )

        self.assertEqual(results["leaderboard"][0]["name"], "score")
        self.assertIsNone(results["leaderboard"][0]["value"])

    def test_custom_output_mode_error_only(self):
        def wrapped():
            raise ValueError("This is a test error")

        results = TestDecorators.run_test_with_decorators(
            decorators=[custom_output(format="html", mode="error_only"), weight(2)],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["status"], "failed")
        self.assertEqual(results["tests"][0]["output_format"], "html")
        self.assertEqual(results["tests"][0]["output"], "Test Failed: This is a test error\n")

    def test_custom_output_mode_replace(self):
        def wrapped(set_custom_output=None):
            set_custom_output("Output will be overridden!")
            raise ValueError("This is a test error")

        results = TestDecorators.run_test_with_decorators(
            decorators=[custom_output(format="html", mode="replace"), weight(2)],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["status"], "failed")
        self.assertEqual(results["tests"][0]["output_format"], "html")
        self.assertEqual(results["tests"][0]["output"], "Output will be overridden!")

    def test_custom_output_mode_append(self):
        def wrapped(set_custom_output=None):
            set_custom_output("Output will be appended!")
            raise ValueError("This is a test error")

        results = TestDecorators.run_test_with_decorators(
            decorators=[custom_output(format="html", mode="append"), weight(2)],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["status"], "failed")
        self.assertEqual(results["tests"][0]["output_format"], "html")
        self.assertEqual(
            results["tests"][0]["output"],
            "Test Failed: This is a test error\n\nOutput will be appended!"
        )

    def test_custom_output_timeout_weight_stacking_1(self):
        def wrapped(set_custom_output=None):
            set_custom_output("Here is my output message.")
            assert 1 == 1, "WTF"

        results = TestDecorators.run_test_with_decorators(
            decorators=[custom_output(format="html", mode="replace"), timeout(1), weight(2)],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["status"], "passed")
        self.assertEqual(results["tests"][0]["max_score"], 2)
        self.assertEqual(results["tests"][0]["score"], 2)
        self.assertEqual(results["tests"][0]["output_format"], "html")
        self.assertEqual(results["tests"][0]["output"], "Here is my output message.")

    def test_custom_output_timeout_weight_stacking_2(self):
        def wrapped(set_custom_output=None):
            set_custom_output("Here is my output message.")
            assert 1 == 1, "WTF"

        results = TestDecorators.run_test_with_decorators(
            decorators=[weight(2), timeout(1), custom_output(format="html", mode="replace")],
            fn=wrapped,
        )

        self.assertEqual(results["tests"][0]["status"], "passed")
        self.assertEqual(results["tests"][0]["max_score"], 2)
        self.assertEqual(results["tests"][0]["score"], 2)
        self.assertEqual(results["tests"][0]["output_format"], "html")
        self.assertEqual(results["tests"][0]["output"], "Here is my output message.")


if __name__ == "__main__":
    unittest.main()
