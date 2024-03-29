from argparse import ArgumentError
from typing import List, Optional, Tuple, Dict, Any

import yaml

from pipyawc.modules import (
    CONSTRUCTORS,
    AdvJob,
    Controller,
    Dispenser,
    Messenger,
    Routine,
    Step,
)

from .arg_funcs import at, delay_for, delay_until, on, schedule_in

TIME_FMT = "%m/%d/%Y: %H:%M:%S"


def _set_at_in(controller: Controller, args: dict, job: Optional[AdvJob]) -> AdvJob:
    if args["at"]:
        if job:
            job = at(args["at"], job)
        else:
            job = at(args["at"], controller.schedule)
    elif args["in"]:
        job = schedule_in(args["in"], controller.schedule)

    if job is None:
        arg_str = ", ".join([f"{k} = {v}" for k, v in args.items()])
        raise ArgumentError(
            argument=None, message=f"Invalid job schedule settings: {arg_str}"
        )

    return job


def run(args: dict, controller: Controller) -> Tuple[bool, str]:
    """
    Schedules a specific routine (by name, requires use of quotations) at the
    specified time

    Ex:
        run [routine] --in [interval] [unit]
        run [routine] --at [HH:MM:SS]
        run [routine] --on [DAY] --at [HH:MM:SS]

    --in takes a single interval/unit pair (i.e. 5 minutes)
    --at takes a specific 24-hr time in format HH:MM:SS
    --on takes a day of the week and should be accompanied by --at
    --repeat is a true/false flag for whether to run the job repeatedly or a
      single time.

    Parameters
    ----------
    args : dict
        A dictionary containing the results of a parsed command line string
    controller : Controller
        The active controller instance

    Returns
    -------
    Tuple[bool, str]
        A tuple consisting of the success/failure status (bool) and a
        descriptive message to return to the user.
    """
    routine_name = args["routine"]
    if not (routine_name in controller.routines.keys()):
        return (False, f"Invalid routine name: {routine_name}!")

    if args["on"]:
        job = on(args["on"], controller.schedule)
    else:
        job = None

    job = _set_at_in(controller, args, job)

    job.run_once = not args["repeat"]

    if args["repeat"]:
        job.tag("Repeating")
    else:
        job.tag("One-Time")
    job.tag(args["routine"])

    job.do(controller.run, name=args["routine"])

    return (True, f"New job scheduled!\n{job.to_string(TIME_FMT)}")


def __report_multiple_jobs(jobs: List[AdvJob]) -> Tuple[bool, str]:
    job_descriptions = []
    for j in jobs:
        job_descriptions.append(f"{j}: ({', '.join([str(t) for t in j.tags])})")
    return (False, f"{len(jobs)} jobs were found: {'; '.join(job_descriptions)}.")


def pause(args: dict, controller: Controller) -> Tuple[bool, str]:
    """
    Takes a job tag, which is required to be uniquely assigned to a single job
    and delays that job until the indicated time.

    Ex:
        pause [job_tag] --until [fuzzy] [time] [string]
        pause [job_tag] --for [interval1] [unit1] ... [intervalN] [unit N]

    --until attempts to process a fuzzy timestring (i.e. next Friday at 5PM)
    --for takes a list of intervals/units (i.e. 5 minutes 6 seconds)

    Parameters
    ----------
    args : dict
        A dictionary containing the results of a parsed command line string
    controller : Controller
        The active controller instance

    Returns
    -------
    Tuple[bool, str]
        A tuple consisting of the success/failure status (bool) and a
        descriptive message to return to the user.
    """
    jobs: List[AdvJob] = controller.schedule.get_jobs_from_tags(
        tags=args["job_tags"]
    )  # type: ignore[assignment]

    if len(jobs) > 1:  # More than one job found, report this back.
        return __report_multiple_jobs(jobs)
    else:  # One job found, let's proceed
        job = jobs[0]

        try:  # Attempt to use the delay function
            if "for" in args:
                job = delay_for(args["for"], job)
            elif "until" in args:
                job = delay_until(args["until"], job)
        except ValueError as e:  # If an error was raised, return it as a string
            return (False, str(e))

    # Report successful delay
    assert job.next_run is not None
    new_time = job.next_run.strftime(TIME_FMT)
    return (True, f"Job: {job.to_string()} has been delayed until {new_time}.")


def cancel(args: dict, controller: Controller) -> Tuple[bool, str]:
    """
    Takes a job tag, which is required to be uniquely assigned to a single job
    and cancels that job.

    Ex:
        cancel [job_tag]

    Parameters
    ----------
    args : dict
        A dictionary containing the results of a parsed command line string
    controller : Controller
        The active controller instance

    Returns
    -------
    Tuple[bool, str]
        A tuple consisting of the success/failure status (bool) and a
        descriptive message to return to the user.
    """
    job_tags = args["jobtags"]
    jobs: List[AdvJob] = controller.schedule.get_jobs_from_tags(tags=job_tags)

    if len(jobs) > 1:  # More than one job found, report this back.
        return __report_multiple_jobs(jobs)
    elif len(jobs) == 1:  # Only one job, let's proceed
        job = jobs[0]
        job_str = job.to_string()
        job.cancel()
        return (True, f"Job: {job_str} cancelled!")
    else:
        return (True, f"No matching jobs for tags: {job_tags}")


def routine(args: dict, controller: Controller) -> Tuple[bool, str]:
    """
    Returns a description of the routine with that name.

    Ex:
        routine [routine_name]

    Parameters
    ----------
    args : dict
        A dictionary containing the results of a parsed command line string
    controller : Controller
        The active controller instance

    Returns
    -------
    Tuple[bool, str]
        A tuple consisting of the success/failure status (bool) and a
        descriptive message to return to the user.
    """
    routine = args["routine"]
    routine = controller.routines[routine]

    return (True, str(routine))


def get_sched(args: dict, controller: Controller) -> Tuple[bool, str]:
    """
    Returns a string listing the current schedule.

    Ex:
        get-sched

    Parameters
    ----------
    args : dict
        A dictionary containing the results of a parsed command line string
    controller : Controller
        The active controller instance

    Returns
    -------
    Tuple[bool, str]
        A tuple consisting of the success/failure status (bool) and a
        descriptive message to return to the user.
    """
    _ = args
    return (True, controller.current_schedule)


def start(args: dict) -> Tuple[Controller, int]:
    """Instatiates the controller object and returns the # of seconds to pause
    between main() loops

    Parameters
    ----------
    args : dict
        A dictionary containing the results of a parsed command line string

    Returns
    -------
    Tuple[Controller, int]
        A tuple of values to pass into the main() function (an instance of
        :class: Controller and the interval between loop runs.)
    """
    for tag, constructor in CONSTRUCTORS.items():
        yaml.add_constructor(tag, constructor, yaml.SafeLoader)

    with open(args["source"], "rb") as c:
        config = yaml.load(c, Loader=yaml.SafeLoader)

    settings = config["settings"]

    messenger = Messenger(check_delay_sec=settings["check_delay_sec"])
    msg_setting: Dict[str, Any] = settings["messenger"]
    for contact in msg_setting.get("contacts", []):
        messenger.register_contact(contact)
    for receiver in msg_setting.get("receivers", []):
        messenger.register_receiver(receiver)
    dispenser = Dispenser(**settings["dispenser"])

    controller = Controller(messenger=messenger, dispenser=dispenser)

    for es in config["error_sensors"]:
        controller.monitor.register(sensor_type="error", **es)

    for ts in config["tank_sensors"]:
        controller.monitor.register(sensor_type="tank", **ts)

    for p in config["pumps"]:
        controller.dispenser.register(**p)

    for r in config["routines"]:
        if any(["_model" in s for s in r["steps"]]):
            raise ValueError(
                "The '_model' parameter should not be manually"
                + "provided for routine steps"
            )

        r["steps"] = [Step(**s) for s in r["steps"]]
        routine = Routine(**r)

        for s in routine.steps:
            s.parent = routine

        controller.register_routine(routine)

    return (controller, args["interval"])
