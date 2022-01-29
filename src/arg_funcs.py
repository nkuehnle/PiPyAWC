# Default module imports
import datetime as dt
import re
import sys
from typing import List, Tuple, Union
if sys.version_info >= (3, 10):
    from itertools import pairwise
else: # Compatibilty for pre-3.10 python
    from itertools import tee
    def pairwise(iterable):
        """
        pairwise('ABCDEFG') --> AB BC CD DE EF FG
        """
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)
# Third-party module imports
from dateutil.parser import ParserError as DTParserError
from dateutil.parser import parse as dtparse
# Custom module imports
from .modules.operations import AJob, AScheduler

# Constants
DAYS = ('sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
        'saturday')
UNITS = ('seconds','minutes','hours','days','weeks','months')
SINGULAR_UNITS = ('second','minute','hour','day','week','month')
TIME_FMT = '%m/%d/%Y: %H:%M:%S'

def at(string: str, target: Union[AScheduler, AJob]) -> AJob:
    """[summary]

    Parameters
    ----------
    string : str
        [description]
    target : Union[AScheduler, AJob]
        [description]

    Returns
    -------
    AJob
        [description]

    Raises
    ------
    ValueError
        [description]
    """
    if not re.match(r"^([0-2]\d:)?[0-5]\d:[0-5]\d$", string):
        raise ValueError("Invalid format, must be given as HH:MM or HH:MM:SS.")
    
    if isinstance(target, AJob):
        job = target
    elif isinstance(target, AScheduler):
        job = target.every().day

    job = job.at(string)

    return job


def on(string: str, schedule: AScheduler) -> AJob:
    """[summary]

    Parameters
    ----------
    string : str
        [description]
    schedule : AScheduler
        [description]

    Returns
    -------
    AJob
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

    job = getattr(job, day) # Calls a property that sets the proper day
    return job


def _process_timespan(terms: Tuple[str]) -> Tuple[int, str]:
    """[summary]

    Parameters
    ----------
    terms : str
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
        raise ValueError(f"Time interval must be >= 1")

    if right in unit_set:
        unit = right
    else:
        val_units = ', '.join([i for i in unit_set])
        raise KeyError(f"Invalid units for interval, {interval}, please select from the following: {val_units}")

    return (interval, unit)


def schedule_in(terms: List[str], schedule: AScheduler) -> AJob:
    num_terms = len(terms)

    if num_terms != 2:
        raise ValueError(f"Timespan contained {num_terms} terms, should take form 'interval unit'")

    interval, unit = _process_timespan(terms)

    job = schedule.every(interval)
    job = getattr(job, unit) # Calls a property that sets the proper unit
    
    return job


def delay_for(terms: List[str], job: AJob) -> AJob:
    """[summary]

    Parameters
    ----------
    terms : List[str]
        [description]
    job : AJob
        [description]

    Returns
    -------
    AJob
        [description]
    """
    td_kwargs = {}

    for l,r in pairwise(terms):
        interval, unit = _process_timespan([l,r])
        td_kwargs[unit] = interval
    
    offset = dt.timedelta(**td_kwargs)

    job.next_run += offset
    
    return job

def delay_until(terms: List[str], job: AJob) -> AJob:
    fuzzy_dt_str = ' '.join(terms)

    try:
        new_dt = dtparse(fuzzy_dt_str, fuzzy=True)
    except DTParserError:
        err = f'The provided delay: "{fuzzy_dt_str}" could not be parsed'
        raise ValueError(err)

    if job.next_run < new_dt:
        job.next_run = new_dt
    else:
        ot = job.next_run.strftime(TIME_FMT)
        nt = new_dt.strftime(TIME_FMT)
        err = f'The new time {nt} occurs before the current runtime {ot}.'
        raise ValueError(err)

    return job
