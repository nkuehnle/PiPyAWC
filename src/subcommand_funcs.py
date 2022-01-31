# Default modules
from typing import Tuple
# Third-party modules
from yaml import load, SafeLoader
# Custom modules
from .arg_funcs import on, schedule_in, at, delay_for, delay_until
from .modules import Controller, Messenger, Step, Routine, Dispenser

TIME_FMT = '%m/%d/%Y: %H:%M:%S'

def run(args: dict, controller: Controller) -> Tuple[bool, str]:
    """
    Schedules a specific routine (by name, requires use of quotations) at the
    specified time

    run [routine] --in [interval] [unit] OR --at [HH:MM:SS] OR --on [DAY] --at [HH:MM:SS]

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
    if not(args['routine'] in controller.routines.keys()):
        return (0, f"Invalid routine name!")

    if args['on']:
        job = on(args['on'], controller.schedule)
    else:
        job = None

    if 'at' in args:
        if job:
            job = at(args['at'], job)
        else:
            job = at(args['at'], controller.schedule)
    elif 'in' in args:
        job = schedule_in(args['in'], controller.schedule)

    job.run_once = not(args['repeat'])

    if args['repeat']:
        job.tag('Repeating')
    else:
        job.tag('One-Time')
    job.tag(args['routine'])

    job.do(controller.run_routine, name=args['routine'])

    return (1, f"New job scheduled!\n{job.to_string(TIME_FMT)}")


def pause(args: dict, controller: Controller) -> Tuple[bool, str]:
    """
    Takes a job tag, which is required to be uniquely assigned to a single job
    and delays that job until the indicated time.

    pause [job_tag] --until [fuzzy] [time] [string] OR --for [interval1] [unit1] ... [intervalN] [unit N]

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
    args = vars(args)
    
    jobs = controller.schedule.get_jobs_from_tags(args['jobtags'])

    if len(jobs) > 1: # More than one job found, report this back.
        for i,j in enumerate(jobs):
            jobs[i] = f"{j}: ({', '.join(j.tags)})"
        return (0, f"Multiple jobs were found {'; '.join(jobs)}.")

    else: # One job found, let's proceed
        job = jobs[0]
        
        try: # Attempt to use the delay function
            if 'for' in args:
                job = delay_for(args['for'], job)
            elif 'until' in args:
                job = delay_until(args['until'], job)
        except ValueError as e: # If an error was raised, return it as a string
            return (0, str(e))

    # Report successful delay
    new_time = job.next_run.strftime(TIME_FMT)
    return (1, f'Job: {job.to_string()} has been delayed until {new_time}.')


def cancel(args: dict, controller: Controller) -> Tuple[bool, str]:
    """
    Takes a job tag, which is required to be uniquely assigned to a single job
    and cancels that job.

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
    jobs = controller.schedule.get_jobs_from_tags(args['jobtags'])

    if len(jobs) > 1: # Report that more than one job was found.
        for i,j in enumerate(jobs):
            jobs[i] = f"{j}: ({', '.join(j.tags)})"
        return (0, f"Multiple jobs were found {'; '.join(jobs)}.")
    elif len(jobs) == 1: # Only one job, let's proceed
        job = jobs[0]
        job_str = job.to_string()
        job.cancel_job()
        return (1, f"Job: {job_str} cancelled!")
    else:
        return (1, f"No matching jobs found!")

def routine(args: dict, controller: Controller) -> Tuple[bool, str]:
    """
    Returns a description of the routine with that name.
    
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
    routine = args['routine']
    routine = controller.routines[routine]

    return (1, str(routine))

def get_sched(args: dict, controller: Controller) -> Tuple[bool, str]:
    """
    Returns a string listing the current schedule.
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
    return 1, controller.current_schedule


def start(args: dict) -> Tuple[Controller, int]:
    """[summary]

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
    with open(args['source'], 'rb') as c:
        config = load(c, SafeLoader)
    
    settings = config['settings']

    messenger = Messenger(**settings['messenger'])
    dispenser = Dispenser(**settings['dispenser'])
    controller = Controller(messenger = messenger,
                            dispenser = dispenser,
                            **settings['controller'])
    
    for es in config['error_sensors']:
        controller.monitor.register(sensor_type='error', **es)

    for ts in config['tank_sensors']:
        controller.monitor.register(sensor_type='tank', **ts)

    for p in config['pumps']:
        controller.dispenser.register(**p)

    for r in config['routines']:

        if any(['_model' in s for s in r['steps']]):
            raise ValueError("The '_model' parameter should not be manually"+\
                "provided for routine steps")

        r['steps'] = [Step(**s) for s in r['steps']]
        routine = Routine(**r)
        controller.register_routine(routine)
        controller.update_routine(routine.name)
    
    return (controller, args['interval'])