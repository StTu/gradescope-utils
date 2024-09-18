import os
import unittest
from gradescope_utils.autograder_utils.rate_limit import (
    prepend_rate_limit_warning,
    get_earlier_results_if_rate_limited,
    read_metadata,
)
from datetime import datetime, timedelta, timezone
import json


class TestRateLimiterNoLimit(unittest.TestCase):
    def test_get_earlier_results(self):
        results = get_earlier_results_if_rate_limited(
            max_per_hour=None,
            max_per_day=None,
            max_total=None,
            metadata_file="tests/test_metadata.json",
        )
        self.assertIsNone(results)

    def test_prepend_rate_limit_warning(self):
        metadata = read_metadata(metadata_file="tests/test_metadata.json")
        prev = metadata["previous_submissions"][0]

        assert not any("Submission Limit Exceeded" in t["name"] for t in prev["results"]["tests"])

        prepend_rate_limit_warning(prev, reason="WXYZ Rate limited WXYZ")

        assert any("Submission Limit Exceeded" in t["name"] for t in prev["results"]["tests"])
        assert "Submission Limit Exceeded" in prev["results"]["tests"][0]["name"]


class TestRateLimiterWithHourLimit(unittest.TestCase):
    tmp_metadata_file = "tests/test_metadata_hour_limit.json"

    @classmethod
    def setUpClass(cls):
        # Create a new dummy metadata file with all recent submissions
        metadata_base = read_metadata(metadata_file="tests/test_metadata.json")
        for i, submission in enumerate(metadata_base["previous_submissions"]):
            dummy_time = datetime.now(tz=timezone(timedelta())) - timedelta(minutes=5) * (i + 1)
            submission["submission_time"] = dummy_time.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
        with open(cls.tmp_metadata_file, "w") as f:
            json.dump(metadata_base, f, indent=4)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.tmp_metadata_file)

    def setUp(self):
        with open(self.tmp_metadata_file, "r") as f:
            metadata = json.load(f)
        self.num_submissions = len(metadata["previous_submissions"])
        assert self.num_submissions > 0, "invalid metadata... can't actually run tests"

    def test_get_earlier_results_unlimited(self):
        results = get_earlier_results_if_rate_limited(
            max_per_hour=None,
            max_per_day=None,
            max_total=None,
            metadata_file=self.tmp_metadata_file,
        )
        self.assertIsNone(results)

    def test_get_earlier_results_hour_limited(self):
        results = get_earlier_results_if_rate_limited(
            max_per_hour=self.num_submissions,
            max_per_day=None,
            max_total=None,
            metadata_file=self.tmp_metadata_file,
        )
        self.assertIsNotNone(results)

    def test_get_earlier_results_hour_limited_one_avail(self):
        results = get_earlier_results_if_rate_limited(
            max_per_hour=self.num_submissions + 1,
            max_per_day=None,
            max_total=None,
            metadata_file=self.tmp_metadata_file,
        )
        self.assertIsNone(results)


class TestRateLimiterWithHourLimitPreviouslyLimited(unittest.TestCase):
    tmp_metadata_file = "tests/test_metadata_hour_limit_2.json"

    @classmethod
    def setUpClass(cls):
        # Create a new dummy metadata file with all recent submissions
        metadata_base = read_metadata(metadata_file="tests/test_metadata.json")
        for i, submission in enumerate(metadata_base["previous_submissions"]):
            dummy_time = datetime.now(tz=timezone(timedelta())) - timedelta(minutes=5) * (i + 1)
            submission["submission_time"] = dummy_time.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
        metadata_base["previous_submissions"][-1]["results"]["extra_data"] = {"rate_limited": True}
        with open(cls.tmp_metadata_file, "w") as f:
            json.dump(metadata_base, f, indent=4)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.tmp_metadata_file)

    def setUp(self):
        with open(self.tmp_metadata_file, "r") as f:
            metadata = json.load(f)
        self.num_submissions_not_limited = len(metadata["previous_submissions"]) - 1
        assert self.num_submissions_not_limited > 0, "invalid metadata... can't actually run tests"

    def test_get_earlier_results_unlimited(self):
        results = get_earlier_results_if_rate_limited(
            max_per_hour=None,
            max_per_day=None,
            max_total=None,
            metadata_file=self.tmp_metadata_file,
        )
        self.assertIsNone(results)

    def test_get_earlier_results_hour_limited(self):
        results = get_earlier_results_if_rate_limited(
            max_per_hour=self.num_submissions_not_limited,
            max_per_day=None,
            max_total=None,
            metadata_file=self.tmp_metadata_file,
        )
        self.assertIsNotNone(results)

    def test_get_earlier_results_hour_limited_one_avail(self):
        results = get_earlier_results_if_rate_limited(
            max_per_hour=self.num_submissions_not_limited + 1,
            max_per_day=None,
            max_total=None,
            metadata_file=self.tmp_metadata_file,
        )
        self.assertIsNone(results)
