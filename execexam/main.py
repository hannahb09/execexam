"""Run an executable examination."""

import io
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import pytest
import typer
from pytest_jsonreport.plugin import JSONReport
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

# create a Typer object to support the command-line interface
cli = typer.Typer(no_args_is_help=True)

# create a default console
console = Console()

# create the skip list for data not needed
skip = ["keywords", "setup", "teardown"]


def path_to_string(path_name: Path, levels: int = 4) -> str:
    """Convert the path to an elided version of the path as a string."""
    parts = path_name.parts
    if len(parts) > levels:
        return Path("<...>", *parts[-levels:]).as_posix()
    else:
        return path_name.as_posix()


def extract_details(details: Dict[Any, Any]) -> str:
    """Extract the details of a dictionary and return it as a string."""
    output = []
    # iterate through the dictionary and add each key-value pair
    for key, value in details.items():
        output.append(f"{value} {key}")
    return "Details: " + ", ".join(output)


def extract_test_run_details(details: Dict[Any, Any]) -> str:
    """Extract the details of a test run."""
    # Format of the data in the dictionary:
    # 'summary': Counter({'passed': 2, 'total': 2, 'collected': 2})
    summary_details = details["summary"]
    # convert the dictionary of summary to a string
    summary_details_str = extract_details(summary_details)
    return summary_details_str


def extract_failing_test_details(
    details: dict[Any, Any]
) -> Tuple[str, Union[Path, None]]:
    """Extract the details of a failing test."""
    # extract the tests from the details
    tests = details["tests"]
    # create an empty string that starts with a newline;
    # the goal of the for loop is to incrementally build
    # of a string that contains all deteails about failing tests
    failing_details_str = "\n"
    # create an initial path for the file containing the failing test
    failing_test_path = None
    # incrementally build up results for all of the failing tests
    for test in tests:
        if test["outcome"] == "failed":
            # convert the dictionary of failing details to a string
            # and add it to the failing_details_str
            failing_details = test
            # get the nodeid of the failing test
            failing_test_nodeid = failing_details["nodeid"]
            failing_details_str += f"  Name: {failing_test_nodeid}\n"
            # get the call information of the failing test
            failing_test_call = failing_details["call"]
            # get the crash information of the failing test's call
            failing_test_crash = failing_test_call["crash"]
            # get all needed information about the test crash call
            failing_test_path = Path(failing_test_crash["path"])
            failing_test_path_str = path_to_string(failing_test_path, 4)
            failing_test_lineno = failing_test_crash["lineno"]
            failing_test_message = failing_test_crash["message"]
            # assemble all of the failing test details into the string
            failing_details_str += f"  Path: {failing_test_path_str}\n"
            failing_details_str += f"  Line number: {failing_test_lineno}\n"
            failing_details_str += f"  Message: {failing_test_message}\n"
    # return the string that contains all of the failing test details
    return (failing_details_str, failing_test_path)


def is_failing_test_details_empty(details: str) -> bool:
    """Determine if the string contains a newline as a hallmark of no failing tests."""
    if details == "\n":
        return True
    return False


@cli.command()
def run(
    project: Path = typer.Argument(
        ...,
        help="Project directory containing questions and tests",
    ),
    tests: Path = typer.Argument(
        ...,
        help="Test file or test directory",
    ),
    verbose: bool = typer.Option(False, help="Display verbose output"),
) -> None:
    """Run an executable exam."""
    return_code = 0
    # add the project directory to the system path
    sys.path.append(str(project))
    # create the plugin that will collect all data
    # about the test runs and report it as a JSON object;
    # note that this approach avoids the need to write
    # a custom pytest plugin for the executable examination
    plugin = JSONReport()
    # display basic diagnostic information about command-line
    # arguments using an emoji and the rich console
    diagnostics = f"\nProject directory: {project}\n"
    diagnostics += f"Test file or test directory: {tests}\n"
    console.print()
    console.print(
        Panel(
            Text(diagnostics, overflow="fold"),
            expand=True,
            title=":sparkles: Parameter Information",
        )
    )
    # run pytest for either:
    # - a single test file that was specified in tests
    # - a directory of test files that was specified in tests
    # note that this relies on pytest correctly discovering
    # all of the test files and running their test cases
    # redirect stdout and stderr to /dev/null
    captured_output = io.StringIO()
    sys.stdout = captured_output
    sys.stderr = captured_output
    # run pytest in a fashion that will not
    # produce any output to the console
    pytest.main(
        [
            "-q",
            "-ra",
            "-s",
            "--json-report-file=none",
            "-p",
            "no:logging",
            "-p",
            "no:warnings",
            "--tb=no",
            os.path.join(tests),
        ],
        plugins=[plugin],
    )
    # restore stdout and stderr; this will allow
    # the execexam program to continue to produce
    # output in the console
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    # extract information about the test run from plugin.report
    # --> display details about the test runs
    test_run_details = extract_test_run_details(plugin.report)  # type: ignore
    console.print()
    console.print(
        Panel(
            Text(
                "\n" + captured_output.getvalue() + test_run_details + "\n",
                overflow="fold",
            ),
            expand=True,
            title=":snake: Test output",
        )
    )
    # --> display details about the failing tests,
    # if they exist. Note that there can be:
    # - zero failing tests
    # - one failing test
    # - multiple failing tests
    (failing_test_details, failing_test_path) = extract_failing_test_details(plugin.report)  # type: ignore
    if not is_failing_test_details_empty(failing_test_details):
        console.print()
        console.print(
            Panel(
                Text(failing_test_details, overflow="fold"),
                expand=True,
                title=":cry: Failing test details",
            )
        )
        return_code = 1
        # define the command: TODO: add the name of the test!
        # TODO: must be done for all of the failing test cases!
        command = f"symbex test_find_minimum_value -f {failing_test_path}"
        # run the command and collect its output
        process = subprocess.run(
            command, shell=True, check=True, text=True, capture_output=True
        )
        # print the output
        # use rich to display this soure code in a formatted box
        source_code_syntax = Syntax(
            "\n" + process.stdout,
            "python",
            theme="ansi_dark",
        )
        console.print()
        console.print(
            Panel(
                source_code_syntax,
                expand=False,
                title=":package: Failing test code",
            )
        )
    # pretty print the JSON report using rich
    console.print(plugin.report, highlight=True)
    # return the code for the overall success of the program
    # to communicate to the operating system the examination's status
    sys.exit(return_code)
