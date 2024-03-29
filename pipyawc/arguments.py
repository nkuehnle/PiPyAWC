from pathlib import Path

from .convenience_classes import (  # Classes for storing abstract representation of CLI elements
    Argument,
    ExclusiveArgGroup,
    Subcommand,
)
from .subcommand_funcs import (  # Subcommand functions
    cancel,
    get_sched,
    pause,
    routine,
    run,
    start,
)

HOME_DIR = Path(__file__).parents[1]
CONF_PATH = HOME_DIR / "data" / "config.yaml"

# Subcommand: Run

# run [routine]
_routine_kwargs = {
    "action": "store",
    "help": "A valid routine name",
    "type": str,
}
_routine_arg = Argument(flags=["routine"], kwargs=_routine_kwargs)
# run [routine] --in [interval units]
in_kwargs = {
    "action": "store",
    "nargs": "+",
    "help": "A valid length of time and associated units (i.e. 5 minutes)",
    "type": str,
    "dest": "in",
}
in_arg = Argument(flags=["-i", "--in"], kwargs=in_kwargs)
# run [routine] --at [datetime]
at_kwargs = {
    "action": "store",
    "help": "A specific time in the format: HH:MM or HH:MM:SS",
    "type": str,
    "dest": "at",
}
at_arg = Argument(flags=["-a", "--at"], kwargs=at_kwargs)
# Must select between --in or --at
when_group = ExclusiveArgGroup(args=[in_arg, at_arg])
# run [routine] --on [day]
on_kwargs = {
    "action": "store",
    "required": False,
    "help": "A day of the week",
    "type": str,
    "dest": "on",
}
on_arg = Argument(flags=["-o", "--on"], kwargs=on_kwargs)
# run [routine] [--in]/[--at]/[--on --at] --repeat
repeat_kwargs = {
    "action": "store_true",
    "help": "Used to indicate that the job should run periodically.",
    "dest": "repeat",
}
repeat_arg = Argument(flags=["-r", "--repeat"], kwargs=repeat_kwargs)
# Create run subcommand object
run_kwargs = {"description": "Run a job", "client": "remote"}
RUN = Subcommand(
    func=run,
    name="run",
    argsets=[_routine_arg, when_group, on_arg, repeat_arg],
    kwargs=run_kwargs,
)


# pause subcommand
# pause [job_tag1] [job_tag2] ... [job_tagN]
job_kwargs = {
    "nargs": "+",
    "help": "A valid list of job tags (UID recommended)",
    "type": str,
}
job_arg = Argument(flags=["job_tags"], kwargs=job_kwargs)
# pause [job] --until datetime
until_kwargs = {
    "nargs": "+",
    "help": "Any standard or fuzzy timestring (i.e. MM-DD HH:MM:SS, or 5 days from now",
    "type": str,
    "dest": "until",
}
until_arg = Argument(flags=["-u", "--until"], kwargs=until_kwargs)
# pause [job] --for [quantity units]
for_kwargs = {
    "nargs": "+",
    "help": "A valid length of time and its associated units (i.e. 5 minutes)",
    "type": str,
    "dest": "for",
}
for_arg = Argument(flags=["-f", "--for"], kwargs=for_kwargs)
# Must select between --for or --until
delay_group = ExclusiveArgGroup(args=[until_arg, for_arg])
# Create pause subcommand object
pause_kwargs = {"description": "Pause a job", "client": "remote"}
PAUSE = Subcommand(
    func=pause,
    name="pause",
    argsets=[job_arg, delay_group],
    kwargs=pause_kwargs,
)


# cancel [job_tag1] [job_tag2] ... [job_tagN]
cancel_kwargs = {"description": "Cancel a job", "client": "remote"}
CANCEL = Subcommand(
    func=cancel,
    name="cancel",
    argsets=[job_arg],
    kwargs=cancel_kwargs,
)


# get-sched
get_sched_kwargs = {"description": "Return the current schedule", "client": "remote"}
GET_SCHED = Subcommand(
    func=get_sched,
    name="get-sched",
    argsets=[],
    kwargs=get_sched_kwargs,
)


# routine --list --> list available routines
# routine [name] uses routine_arg same as the run command
# routine [name] --update
# pause [job] --for [quantity units]
update_kwargs = {
    "action": "store_true",
    "dest": "update",
    "help": "Re-calculate parameters such as the max runtimes of a routine",
}
update_arg = Argument(flags=["--update"], kwargs=update_kwargs)
routine_kwargs = {"description": "Look-up or modify a routine", "client": "remote"}
ROUTINE = Subcommand(
    func=routine,
    name="routine",
    argsets=[_routine_arg],
    kwargs=routine_kwargs,
)


# start [source]
source_kwargs = {
    "action": "store",
    "required": False,
    "default": CONF_PATH,
    "dest": "source",
    "type": str,
    "help": "A valid path to the configuation file to load.",
}
source_arg = Argument(flags=["--source"], kwargs=source_kwargs)
# start --interval
interval_kwargs = {
    "action": "store",
    "required": False,
    "default": 1,
    "dest": "interval",
    "type": float,
    "help": "A length of time to sleep (in seconds) between checking for pending jobs.",
}
interval_arg = Argument(flags=["--interval"], kwargs=interval_kwargs)
start_kwargs = {
    "description": "Start the program, requires a valid config.yaml file.",
    "client": "standard",
}
START = Subcommand(
    func=start,
    name="start",
    argsets=[source_arg, interval_arg],
    kwargs=start_kwargs,
)


# Define two main CLIs
REMOTE_CLI = [RUN, PAUSE, CANCEL, GET_SCHED, ROUTINE]
STANDARD_CLI = [START]
