import json
from pathlib import Path
from typing import Dict, List
import datetime as dt
from pipyawc import Controller, new_parser, process_remote
from pipyawc.modules.operations import AJob
import shlex

TEST_DIR = Path(__file__).parents[0]
MOCK_CONTROLLER = Controller(routines={"Water_Change": None})


def load_test_commands() -> Dict[str, Dict[str, Dict]]:
    """Load test commands from a JSON file.

    Returns
    -------
    Dict[str, Dict[str, Dict]]
        A dictionary containing test command configurations.
    """
    configs = {}

    with open(TEST_DIR / "commands.json", "r") as f:
        configs = json.load(f)

    return configs


def schedule_mock_routine(add_tags: List[str]) -> AJob:
    """Schedule a mock routine with specified tags.

    Parameters
    ----------
    add_tags : List[str]
        List of tags to assign to the scheduled job.

    Returns
    -------
    AJob
        The scheduled job.
    """
    # Schedule mock routine
    job = MOCK_CONTROLLER.schedule.every(1).days
    job.at("00:00:00")

    for tag in add_tags:
        job.tag(tag)

    job.do(MOCK_CONTROLLER.run_routine, name="Water_Change")

    return job


def reset_controller():
    """Reset the global MOCK_CONTROLLER object."""
    # Replaces schedule with new list
    global MOCK_CONTROLLER
    MOCK_CONTROLLER = Controller(routines={"Water_Change": None})


def parse_mock_command(command: str, parser_type: str) -> dict:
    """Parse a mock command string.

    Parameters
    ----------
    command : str
        The command string to parse.
    parser_type : str
        The type of parser to use for parsing the command.

    Returns
    -------
    dict
        A dictionary containing the parsed command arguments.
    """
    # Each iteration of this loop tests a valid command string
    cli = new_parser(parser_type)
    args = cli.parse_args(shlex.split(command))
    args = vars(args)

    return args


def process_mock_command(command: str, parser_type="remote") -> dt.datetime:
    """Process a mock command.

    Parameters
    ----------
    command : str
        The command string to process.
    parser_type : str, optional
        The type of parser to use for processing the command (default is "remote").

    Returns
    -------
    dt.datetime
        The next run time of the scheduled job.
    """
    # Process mock command
    remote_cli = new_parser(parser_type)
    command = shlex.split("run Water_Change --at 00:00:00")
    args = remote_cli.parse_args(command)
    process_remote(args, MOCK_CONTROLLER, output=False)


def check_job(time: dt.datetime, correct_time: dt.datetime):
    """Check if a job's next run time matches the correct time.

    Parameters
    ----------
    time : dt.datetime
        The job's next run time to check.
    correct_time : dt.datetime
        The correct next run time to compare against.
    """
    time_diff = time - correct_time
    print(time_diff)
    assert time_diff <= dt.timedelta(seconds=3)


def run(command: str) -> dt.datetime:
    """Run a command and return the next job time.

    Parameters
    ----------
    command : str
        The command string to run.

    Returns
    -------
    dt.datetime
        The next run time of the scheduled job.
    """
    reset_controller()
    process_mock_command(command)
    job_time = MOCK_CONTROLLER.schedule.jobs[0].next_run

    return job_time


def pause(command: str) -> dt.datetime:
    """Pause a routine and return the next job time.

    Parameters
    ----------
    command : str
        The command string to pause the routine.

    Returns
    -------
    dt.datetime
        The next run time of the scheduled job.
    """
    reset_controller()
    job = schedule_mock_routine(["Repeating"])
    process_mock_command(command)
    job_time = job.next_run

    return job_time
