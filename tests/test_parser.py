import _parser_helpers as _help
from typing import Tuple
import datetime as dt

CONTROLLER = _help.CONTROLLER
TEST_COMMANDS = _help.load_test_commands()

def test_string_parsing():
    for subcommand, test_data in TEST_COMMANDS.items():
        # Each iteration of this loop tests a different subcommand
        if subcommand == 'start':
            parser_type = 'standard'
        else:
            parser_type = 'remote'

        for command, expected_dict in test_data.items():
            # Each iteration of this loop tests a valid command string
            args = _help.parse_mock_command(command, parser_type)

            valid_vars = args.items() >= expected_dict.items()

            if not(valid_vars):
                for k, v in expected_dict.items():
                    if args[k] != v:
                        print(args[k])
                    assert((k in args.keys()) and (v == args[k]))

def test_run():
    """
    A unit test for different run commands
    """
    _help.process_mock_command("run Water_Change --at 00:00:00")

    #Determine correct timing
    correct_time = dt.datetime.today()
    correct_time = correct_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if dt.datetime.today().strftime("%HH:%MM:%SS") != "00:00:00":
        correct_time = correct_time + dt.timedelta(days=1)

    #Check if command was properly executed
    jobs = CONTROLLER.schedule.get_jobs("Water_Change")
    assert(any(jobs))

    for j  in jobs:
        assert(j.next_run == correct_time)

    CONTROLLER.schedule.jobs = []

def test_pause():
    """
    A unit test for different pause commands
    """
    def _pause_helper(command: str) -> Tuple[dt.datetime, dt.datetime]:
        _help.reset_controller()
        job = _help.schedule_mock_routine(["Repeating"])
        initial_time = job.next_run
        processing_time= _help.process_mock_command(command)

        return (initial_time, processing_time, job.next_run)
    
    times = _pause_helper("pause Water_Change Repeating --until \"tomorrow at 5\"")
    #Determine correct timing
    correct_time = dt.datetime.today() + dt.timedelta(days=1)
    correct_time = correct_time.replace(hour=5, minute=0, second=0, microsecond=0)
    #Check timing
    time_diff1 = times[2] - correct_time
    assert(time_diff1 <= dt.timedelta(seconds=1))


    times = _pause_helper("pause Water_Change --until 00:00:00")
    #Determine correct timing
    correct_time = dt.datetime.today()
    correct_time = correct_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if dt.datetime.today().strftime("%HH:%MM:%SS") != "00:00:00":
        correct_time = correct_time + dt.timedelta(days=1)

    time_diff2 = times[2] - correct_time
    assert(time_diff2 <= dt.timedelta(seconds=1))

    times = _pause_helper("pause Water_Change --until friday at 5PM")
    #Determine correct timing
    today = dt.datetime.today()
    friday = today + dt.timedelta((4-today.weekday()) % 7)
    correct_time = friday.replace(hour=17, minute=0, second=0, microsecond=0)
    #Check timing
    time_diff3 = times[2] - correct_time
    assert(time_diff3 <= dt.timedelta(seconds=1))


    times = _pause_helper("pause Water_Change --for 10 minutes")
    #Determine correct timing
    correct_time = times[0] + dt.timedelta(minutes=10)
    #Check timing
    time_diff4 = times[2] - correct_time
    assert(time_diff4 <= dt.timedelta(seconds=1))