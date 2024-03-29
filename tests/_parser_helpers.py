import datetime as dt
import json
import shlex
from pathlib import Path
from typing import Dict, List

from pipyawc import Controller, new_parser, process_remote
from pipyawc.modules.services import AdvJob, Messenger
from pipyawc.modules.logistics import Routine

TEST_DIR = Path(__file__).parents[0]
MOCK_ROUTINE = Routine(
    name="Water_Change",
    interval=0,
    unit="seconds",
    priority=0,
    steps=[],
)
MOCK_CONTROLLER = Controller(
    messenger=Messenger(), routines={"Water_Change": MOCK_ROUTINE}
)


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


def schedule_mock_routine(add_tags: List[str]) -> AdvJob:
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

    job.do(MOCK_CONTROLLER.run, name="Water_Change")

    return job


def reset_controller():
    """Reset the global MOCK_CONTROLLER object."""
    # Replaces schedule with new list
    global MOCK_CONTROLLER
    MOCK_CONTROLLER = Controller(messenger=Messenger(), routines={"Water_Change": None})


def parse_mock_command(command: str, parser_type: str) -> Dict[str, str]:
    """Parse a mock command string.

    Parameters
    ----------
    command : str
        The command string to parse.
    parser_type : str
        The type of parser to use for parsing the command.

    Returns
    -------
    Dict[str, str]
        A dictionary containing the parsed command arguments.
    """
    # Each iteration of this loop tests a valid command string
    cli = new_parser(parser_type)
    args = cli.parse_args(shlex.split(command))
    return {k: v for k, v in vars(args).items()}


def process_mock_command(command: str, parser_type="remote"):
    """Process a mock command.

    Parameters
    ----------
    command : str
        The command string to process.
    parser_type : str, optional
        The type of parser to use for processing the command (default is "remote").
    """
    # Process mock command
    remote_cli = new_parser(parser_type)
    args = remote_cli.parse_args(shlex.split("run Water_Change --at 00:00:00"))
    process_remote(args, MOCK_CONTROLLER, output="")


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
    assert job_time is not None
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
    assert job_time is not None
    return job_time
