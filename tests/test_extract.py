"""Test suite for the extract module."""

import pytest
from hypothesis import given, settings
from hypothesis.strategies import dictionaries, text

from execexam.extract import (
    extract_details,
    extract_failing_test_details,
    extract_test_assertion_details,
    extract_test_assertion_details_list,
    extract_test_assertions_details,
    extract_test_run_details,
)


def test_extract_details():
    """Confirm that extracting details from a dictionary works."""
    details = {"key1": "value1", "key2": "value2", "key3": "value3"}
    result = extract_details(details)
    assert result == "Details: value1 key1, value2 key2, value3 key3"


@settings(max_examples=2)
@given(
    dictionaries(
        keys=text(),
        values=text(),
    )
)
@pytest.mark.fuzz
def test_extract_details_hypothesis(details):
    result = extract_details(details)
    # If the dictionary is empty, the expected result is an empty string
    if not details:
        expected_result = ""
    else:
        expected_result = "Details: " + ", ".join(
            f"{v} {k}" for k, v in details.items()
        )
    assert result == expected_result


def test_extract_test_run_details():
    # check a simple example
    details = {"summary": {"passed": 2, "total": 2, "collected": 2}}
    result = extract_test_run_details(details)
    assert result == "Details: 2 passed, 2 total, 2 collected"
    # check a modified simple example
    details = {"summary": {"failed": 1, "total": 3, "collected": 3}}
    result = extract_test_run_details(details)
    assert result == "Details: 1 failed, 3 total, 3 collected"
    # check a empty example
    details = {"summary": {}}
    result = extract_test_run_details(details)
    assert result == ""


def test_extract_test_assertion_details():
    """Confirm that extract details about a test assertion works."""
    test_details = {
        "assertion1": "value1",
        "assertion2": "value2",
        "assertion3": "value3",
    }
    expected_output = (
        "  - assertion1: value1\n"
        "    assertion2: value2\n"
        "    assertion3: value3\n"
    )
    assert extract_test_assertion_details(test_details) == expected_output


def test_extract_test_assertion_details_list():
    """Confirm that extracting details about a list of test assertions works."""
    test_details_list = [
        {
            "assertion1": "value1",
            "assertion2": "value2",
        },
        {
            "assertion3": "value3",
            "assertion4": "value4",
        },
    ]
    expected_output = (
        "  - assertion1: value1\n"
        "    assertion2: value2\n"
        "  - assertion3: value3\n"
        "    assertion4: value4\n"
    )
    assert (
        extract_test_assertion_details_list(test_details_list)
        == expected_output
    )


def test_extract_test_assertions_details():
    """Confirm that extracting details about test assertions works."""
    test_reports = [
        {
            "nodeid": "/path/to/test_file.py::test_name1",
            "assertions": [
                {
                    "assertion1": "value1",
                    "assertion2": "value2",
                },
            ],
        },
        {
            "nodeid": "/path/to/test_file.py::test_name2",
            "assertions": [
                {
                    "assertion3": "value3",
                    "assertion4": "value4",
                },
            ],
        },
    ]
    expected_output = (
        "\ntest_file.py::test_name1\n"
        "  - assertion1: value1\n"
        "    assertion2: value2\n"
        "\ntest_file.py::test_name2\n"
        "  - assertion3: value3\n"
        "    assertion4: value4\n"
    )
    assert extract_test_assertions_details(test_reports) == expected_output


def test_extract_failing_test_details():
    """Confirm that extracting details about the failing tests works."""
    # define a dictionary that contains details about failing tests
    failing_test_details = {
        "root": "/home/user/project",
        "tests": [
            {
                "outcome": "failed",
                "nodeid": "test_module.py::test_function",
                "call": {"crash": {"lineno": 10, "message": "AssertionError"}},
            },
            {
                "outcome": "passed",
                "nodeid": "test_module.py::test_function2",
                "call": {"crash": {"lineno": 20, "message": "AssertionError"}},
            },
        ],
    }
    # call the function with the failing test details
    result = extract_failing_test_details(failing_test_details)
    # check the result
    assert len(result) == 2  # noqa: PLR2004
    assert (
        result[0]
        == "\n  Name: test_module.py::test_function\n  Path: /home/user/project/test_module.py\n  Line number: 10\n  Message: AssertionError\n"
    )
    assert len(result[1]) == 1
    assert result[1][0]["test_name"] == "test_function"
    assert (
        str(result[1][0]["test_path"]) == "/home/user/project/test_module.py"
    )
