from functools import wraps, update_wrapper
import signal


class _update_wrapper_after_call(object):
    """Context manager to update a wrapper function after the wrapped function is called. Thus,
    if the wrapped function modifies the wrapper state (as in @partial_credit, for example), any
    changes to the wrapper will be preserved.
    """
    def __init__(self, wrapper, func):
        self.wrapper = wrapper
        self.func = func

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        update_wrapper(self.wrapper, self.func)


class weight(object):
    """Simple decorator to add a __weight__ property to a function

    Usage: @weight(3.0)
    """
    def __init__(self, val):
        self.val = val

    def __call__(self, func):
        func.__weight__ = self.val
        return func


class number(object):
    """Simple decorator to add a __number__ property to a function

    Usage: @number("1.1")

    This field will then be used to sort the test results on Gradescope.
    """

    def __init__(self, val):
        self.val = str(val)

    def __call__(self, func):
        func.__number__ = self.val
        return func

class visibility(object):
    """Simple decorator to add a __visibility__ property to a function

    Usage: @visibility("hidden")

    Options for the visibility field are as follows:

    - `hidden`: test case will never be shown to students
    - `after_due_date`: test case will be shown after the assignment's due date has passed.
      If late submission is allowed, then test will be shown only after the late due date.
    - `after_published`: test case will be shown only when the assignment is explicitly published from the "Review Grades" page
    - `visible` (default): test case will always be shown
    """

    def __init__(self, val):
        self.val = val

    def __call__(self, func):
        func.__visibility__ = self.val
        return func


class hide_errors(object):
    """Simple decorator to add a __hide_errors__ property to a function

    Usage: @hide_errors("Error message to be shown upon test failure")

    Used to hide the particular source of an error which caused a test to fail.
    Otherwise, a test's particular assertions can be seen by students.
    """

    def __init__(self, val="Test failed"):
        self.val = val

    def __call__(self, func):
        func.__hide_errors__ = self.val
        return func


class tags(object):
    """Simple decorator to add a __tags__ property to a function

    Usage: @tags("concept1", "concept2")
    """
    def __init__(self, *args):
        self.tags = args

    def __call__(self, func):
        func.__tags__ = self.tags
        return func


class leaderboard(object):
    """Decorator that indicates that a test corresponds to a leaderboard column

    Usage: @leaderboard("high_score"). The string parameter indicates
    the name of the column on the leaderboard

    Then, within the test, set the value by calling
    kwargs['set_leaderboard_value'] with a value. You can make this convenient by
    explicitly declaring a set_leaderboard_value keyword argument, eg.

    ```
    def test_highscore(set_leaderboard_value=None):
        set_leaderboard_value(42)
    ```

    """

    def __init__(self, column_name, sort_order='desc'):
        self.column_name = column_name
        self.sort_order = sort_order

    def __call__(self, func):
        func.__leaderboard_column__ = self.column_name
        func.__leaderboard_sort_order__ = self.sort_order

        def set_leaderboard_value(x):
            wrapper.__leaderboard_value__ = x

        @wraps(func)
        def wrapper(*args, **kwargs):
            kwargs['set_leaderboard_value'] = set_leaderboard_value
            with _update_wrapper_after_call(wrapper, func):
                return func(*args, **kwargs)

        return wrapper


class partial_credit(object):
    """Decorator that indicates that a test allows partial credit

    Usage: @partial_credit(test_weight)

    Then, within the test, set the value by calling
    kwargs['set_score'] with a value. You can make this convenient by
    explicitly declaring a set_score keyword argument, eg.

    ```
    @partial_credit(10)
    def test_partial(set_score=None):
        set_score(4.2)
    ```

    """

    def __init__(self, weight):
        self.weight = weight

    def __call__(self, func):
        func.__weight__ = self.weight

        def set_score(x):
            wrapper.__score__ = x

        @wraps(func)
        def wrapper(*args, **kwargs):
            kwargs['set_score'] = set_score
            with _update_wrapper_after_call(wrapper, func):
                return func(*args, **kwargs)

        return wrapper


class TestTimeout(RuntimeError):
    pass


class timeout:
    """Decorator that sets a time limit on an individual test case, in seconds.
    """
    def __init__(self, seconds, error_message=None):
        if error_message is None:
            error_message = "test timed out after {}s.".format(seconds)
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TestTimeout(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with _update_wrapper_after_call(wrapper, func):
                with self:
                    return func(*args, **kwargs)

        return wrapper


class custom_output(object):
    """Decorator to set the output_format of a test result in results.json, and optionally provide
    a setter function so the test can determine the output at runtime.

    Usage example 1:
    @custom_output(format="simple_format", mode="error_only")
    def mytest():
        raise ValueError(r"This is a custom error message with \n\n newlines and <i>fancy html</i>")

    Usage example 2:
    @custom_output(format="text", mode="append")
    def mytest(set_custom_output=None):
        set_custom_output("This is a custom output message! It will be appended after any errors.")
        raise ValueError("This error message will appear first in the output.")

    Usage example 3:
    @custom_output(format="md", mode="replace")
    def mytest(set_custom_output=None):
        set_custom_output("This is a **custom output message**! It will replace any errors.")
        raise ValueError("This error message will not appear in the output.")
    """

    FORMATS = ["text", "html", "simple_format", "md", "ansi"]
    MODES = ["error_only", "replace", "append"]

    def __init__(self, format="text", mode="error_only"):
        if format not in custom_output.FORMATS:
            raise ValueError(f"format must be one of the gradescope-approved formats: "
                             f"{custom_output.FORMATS}")
        if mode not in custom_output.MODES:
            raise ValueError(f"mode must be one of the following: {custom_output.MODES}")

        self.format = format
        self.mode = mode

    def __call__(self, func):
        func.__output_format__ = self.format
        func.__custom_output_mode__ = self.mode

        def set_custom_output(x):
            wrapper.__custom_output__ = x

        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.mode in ["replace", "append"]:
                kwargs["set_custom_output"] = set_custom_output
            with _update_wrapper_after_call(wrapper, func):
                return func(*args, **kwargs)

        return wrapper

from datetime import datetime, timezone
from typing import Optional, Union
import re

ISO_Z_RE = re.compile(r"Z$")

def _parse_iso8601_utc(s) -> datetime:
    """
    Accepts ISO 8601 like '2025-10-01T09:00:00Z' or with explicit offset.
    Normalizes to timezone-aware UTC.
    """
    if s is None:
        raise ValueError("available_from: timestamp string required")
    
    # If it's already a datetime object, just ensure it's in UTC
    if isinstance(s, datetime):
        if s.tzinfo is None:
            # Treat naive datetime as UTC
            s = s.replace(tzinfo=timezone.utc)
        return s.astimezone(timezone.utc)
    
    # Handle string input
    if not isinstance(s, str):
        raise ValueError(f"available_from: expected string or datetime, got {type(s)}")
    
    s = s.strip()
    # Replace trailing 'Z' with '+00:00' so fromisoformat can parse it
    s = ISO_Z_RE.sub("+00:00", s)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        # Treat naive as UTC to avoid surprises in containers
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class available_from(object):
    """Decorator to make tests available only after a specific date/time.
    
    Usage: 
        @available_from("2025-10-01T09:00:00Z")
        or
        @available_from(datetime(2025, 10, 1, 9, 0, 0, tzinfo=timezone.utc))
    
    Tests with this decorator that have not yet unlocked will be:
    - Skipped during test execution
    - Excluded from the total max score
    - Optionally shown in output with a custom message (depending on runner configuration)
    """

    def __init__(self, when: Union[str, datetime], *, reason: Optional[str] = None):
        self.when = when
        self.reason = reason
        self.unlock_dt = _parse_iso8601_utc(when)

    def __call__(self, func):
        # Attach metadata so the runner can read it before executing
        func.__gs_available_from__ = self.unlock_dt
        if self.reason:
            func.__gs_available_from_reason__ = self.reason

        @wraps(func)
        def wrapper(*args, **kwargs):
            # If someone calls it directly (outside our runner), just run.
            return func(*args, **kwargs)
        return wrapper