# Default module imports
import datetime as dt
import re
from itertools import pairwise
from typing import List, Sequence, Tuple, Union

from dateutil.parser import ParserError as DTParserError
from dateutil.parser import parse as dtparse

from .modules.services import AdvJob, AdvScheduler

# Constants
DAYS = ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday")
UNITS = ("seconds", "minutes", "hours", "days", "weeks", "months")
SINGULAR_UNITS = ("second", "minute", "hour", "day", "week", "month")
TIME_FMT = "%m/%d/%Y: %H:%M:%S"


def at(string: str, target: Union[AdvScheduler, AdvJob]) -> AdvJob:
    """[summary]

    Parameters
    ----------
    string : str
        [description]
    target : AdvScheduler | AdvJob
        [description]

    Returns
    -------
    AdvJob
        [description]

    Raises
    ------
    ValueError
        [description]
    """
    if not re.match(r"^([0-2]\d:)?[0-5]\d:[0-5]\d$", string):
        raise ValueError("Invalid format, must be given as HH:MM or HH:MM:SS.")

    if isinstance(target, AdvJob):
        job = target
    elif isinstance(target, AdvScheduler):
        job = target.every().day

    job = job.at(string)

    return job


def on(string: str, schedule: AdvScheduler) -> AdvJob:
    """[summary]

    Parameters
    ----------
    string : str
        [description]
    schedule : AdvScheduler
        [description]

    Returns
    -------
    AdvJob
        [description]

    Raises
    ------
    ValueError
        [description]
    """
    string = string.lower()

    if string in DAYS:
        day = string
    else:
        raise ValueError(f"Invalid weekday: {string}")

    job = schedule.every()

    job = getattr(job, day)  # Calls a property that sets the proper day
    return job


def _process_timespan(terms: Sequence[str]) -> Tuple[int, str]:
    """[summary]

    Parameters
    ----------
    terms : Sequence[str]
        [description]

    Returns
    -------
    Callable
        [description]

    Raises
    ------
    ValueError
        [description]
    ValueError
        [description]
    KeyError
        [description]
    """
    left = terms[0].lower()
    right = terms[1].lower()

    if left.isnumeric():
        interval = int(left)
    else:
        raise ValueError(f"Invalid schedule interval: {left}")

    if interval == 1:
        unit_set = SINGULAR_UNITS
    elif interval > 1:
        unit_set = UNITS
    else:
        raise ValueError(f"Time interval must be >= 1, received {interval}")

    if right in unit_set:
        unit = right
    else:
        units_str = ", ".join([i for i in unit_set])
        raise KeyError(
            f"Invalid units for interval, {interval}, please select from: {units_str}"
        )

    return (interval, unit)


def schedule_in(terms: List[str], schedule: AdvScheduler) -> AdvJob:
    """_summary_

    Parameters
    ----------
    terms : List[str]
        _description_
    schedule : AdvScheduler
        _description_

    Returns
    -------
    AdvJob
        _description_

    Raises
    ------
    ValueError
        _description_
    """
    num_terms = len(terms)
    if num_terms != 2:
        raise ValueError(
            f"Timespan contained {num_terms} terms, should take form 'interval unit'"
        )

    interval, unit = _process_timespan(terms)

    job = schedule.every(interval)
    getattr(job, unit)  # Calls a property that sets the proper unit

    return job


def delay_for(terms: List[str], job: AdvJob) -> AdvJob:
    """[summary]

    Parameters
    ----------
    terms : List[str]
        [description]
    job : AdvJob
        [description]

    Returns
    -------
    AdvJob
        [description]
    """
    td_kwargs = {}

    for lterm, rterm in pairwise(terms):
        interval, unit = _process_timespan([lterm, rterm])
        td_kwargs[unit] = interval

    offset = dt.timedelta(**td_kwargs)

    if job.next_run is not None:
        job.next_run += offset

    return job


def delay_until(terms: List[str], job: AdvJob) -> AdvJob:
    fuzzy_dt_str = " ".join(terms)

    try:
        new_dt = dtparse(fuzzy_dt_str, fuzzy=True)
    except DTParserError:
        err = f'The provided delay: "{fuzzy_dt_str}" could not be parsed'
        raise ValueError(err)

    if job.next_run is None:
        return job

    if job.next_run < new_dt:
        job.next_run = new_dt
    else:
        ot = job.next_run.strftime(TIME_FMT)
        nt = new_dt.strftime(TIME_FMT)
        err = f"The new time {nt} occurs before the current runtime {ot}."
        raise ValueError(err)

    return job
