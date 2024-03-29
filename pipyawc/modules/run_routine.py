import datetime as dt
from typing import Optional

from schedule import CancelJob

from .logistics import Routine
from .peripherals import Dispenser, ErrorSensorTriggered, Monitor, PumpTimeoutError


def _run(
    routine: Routine,
    dispenser: Dispenser,
    monitor: Monitor,
) -> Optional[CancelJob]:
    routine.start_dt = dt.datetime.now()
    stop = False
    job_ret = None
    for step in routine.steps:
        ret = dispenser.run_step(step, monitor)

        run_time, errs = ret
        routine.errors.append(errs)
        routine.run_times.append(run_time)

        # Case where an initial state error was reported.
        if run_time == 0:
            if step.report_invalid_start:
                routine.error_reports.append(routine.get_err_report(errs[0]))
            if not (step.proceed_on_invalid_start):
                stop = True

        # Case where the initial state was correctly met
        elif run_time > 0:
            # Report and log each individual error encountered.
            for e in errs:
                routine.error_reports.append(routine.get_err_report(e))

                if isinstance(e, PumpTimeoutError):
                    if not (step.proceed_on_timeout):
                        stop = True
                elif isinstance(e, ErrorSensorTriggered):
                    final_run = e.remaining_runs <= 0
                    if not (step.proceed_on_error) and final_run:
                        stop = True

        # Figure out if we need to stop we need to stop early...
        if stop is True:
            if step.cancel_on_critical_failure:
                job_ret = CancelJob()
            break  # End for loop early

    return job_ret


def run(
    routine: Routine,
    dispenser: Dispenser,
    monitor: "Monitor",
) -> Optional[CancelJob]:

    job_ret = _run(routine=routine, dispenser=dispenser, monitor=monitor)
    routine.stop_dt = dt.datetime.now()
    return job_ret
