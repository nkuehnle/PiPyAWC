import json
from pathlib import Path
from typing import Dict, List, Any
import datetime as dt
from pipyawc import Controller, new_parser, process_remote
from pipyawc.modules.operations import AJob
import shlex

TEST_DIR = Path(__file__).parents[0]
CONTROLLER = Controller(routines={"Water_Change": None})

def load_test_commands() -> Dict[str, Dict[str, Dict]]:
    configs = {}

    with open(TEST_DIR/'commands.json', 'r') as f:
        configs = json.load(f)

    return configs

def schedule_mock_routine(add_tags: List[str]) -> AJob:
    #Schedule mock routine
    job = CONTROLLER.schedule.every(1).days
    job.at("00:00:00")

    for tag in add_tags:
        job.tag(tag)

    job.do(CONTROLLER.run_routine, name="Water_Change")

    return job

def reset_controller():
    # Replaces schedule with new list
    CONTROLLER.schedule.jobs = []

def parse_mock_command(command: str, parser_type: str) -> dict:
    # Each iteration of this loop tests a valid command string
    cli = new_parser(parser_type)
    args = cli.parse_args(shlex.split(command))
    args = vars(args)
    
    return args

def process_mock_command(command: str, parser_type='remote') -> dt.datetime:
    #Process mock command
    remote_cli = new_parser(parser_type)
    command = shlex.split("run Water_Change --at 00:00:00")
    args = remote_cli.parse_args(command)
    process_remote(args, CONTROLLER, output=False)
    
    return dt.datetime.now()