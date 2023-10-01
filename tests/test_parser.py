import _parser_helpers as _help
import datetime as dt
import pytest

MOCK_CONTROLLER = _help.MOCK_CONTROLLER
TEST_COMMANDS = _help.load_test_commands()


def test_string_parsing():
    """Test string parsing for different subcommands and commands.

    Iterates through test data and checks if the parsed arguments match the expected dictionary.
    """
    for subcommand, test_data in TEST_COMMANDS.items():
        # Each iteration of this loop tests a different subcommand
        if subcommand == "start":
            parser_type = "standard"
        else:
            parser_type = "remote"

        for command, expected_dict in test_data.items():
            # Each iteration of this loop tests a valid command string
            args = _help.parse_mock_command(command, parser_type)

            valid_vars = args.items() >= expected_dict.items()

            if not (valid_vars):
                for k, v in expected_dict.items():
                    if args[k] != v:
                        print(args[k])
                    assert (k in args.keys()) and (v == args[k])


def test_run():
    """
    A unit test for different run commands.
    """
    print(MOCK_CONTROLLER.schedule.jobs)
    time = _help.run("run Water-Change --at 00:00:00")
    print(MOCK_CONTROLLER.schedule.jobs)
    # Determine correct timing
    correct_time = dt.datetime.today()
    correct_time = correct_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if dt.datetime.today().strftime("%HH:%MM:%SS") != "00:00:00":
        correct_time = correct_time + dt.timedelta(days=1)
    # Check job
    _help.check_job(time, correct_time)

    time = _help.run("run Water-Change --in 5 minutes")
    print(MOCK_CONTROLLER.schedule.jobs)
    # Determine correct timing
    correct_time = dt.datetime.now() + dt.timedelta(minutes=5)
    # Check job
    _help.check_job(time, correct_time)


def test_pause():
    """
    A unit test for different pause commands.
    """
    time = _help.pause('pause Water_Change Repeating --until "tomorrow at 5"')
    # Determine correct timing
    correct_time = dt.datetime.today() + dt.timedelta(days=1)
    correct_time = correct_time.replace(hour=5, minute=0, second=0, microsecond=0)
    # Check timing
    _help.check_job(time, correct_time)

    time = _help.pause("pause Water_Change --until 00:00:00")
    # Determine correct timing
    correct_time = dt.datetime.today()
    correct_time = correct_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if dt.datetime.today().strftime("%HH:%MM:%SS") != "00:00:00":
        correct_time = correct_time + dt.timedelta(days=1)
    # Check timing
    _help.check_job(time, correct_time)

    time = _help.pause("pause Water_Change --until friday at 5PM")
    # Determine correct timing
    today = dt.datetime.today()
    friday = today + dt.timedelta((4 - today.weekday()) % 7)
    correct_time = friday.replace(hour=17, minute=0, second=0, microsecond=0)
    # Check timing
    _help.check_job(time, correct_time)

    time = _help.pause("pause Water_Change --for 10 minutes")
    # Determine correct timing
    correct_time = time + dt.timedelta(minutes=10)
    # Check timing
    _help.check_job(time, correct_time)
