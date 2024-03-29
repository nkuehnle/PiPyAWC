import datetime as dt
from typing import Dict, List, Optional

from schedule import CancelJob

from pipyawc.modules.peripherals import (
    Dispenser,
    ErrorSensorTriggered,
    Monitor,
    PumpTimeoutError,
)

from .steps import Step

TIME_FMT = "%m/%d/%Y: %H:%M:%S"


class Routine:
    """
    Represents a routine consisting of multiple steps.

    Parameters
    ----------
    name : str
        The name of the routine.
    interval : int
        The interval at which the routine runs.
    unit : str
        The unit of time for the interval (e.g., 'minutes', 'hours').
    priority : int
        The priority level of the routine.
    steps : List[Step]
        The list of steps within the routine.
    error_contacts : Tuple[str], optional
        List of error contacts for notification, by default [].
    completion_contacts : Tuple[str], optional
        List of completion contacts for notification, by default [].

    Methods
    -------
    __str__()
        Get a string representation of the routine.

    Attributes
    ----------
    name : str
        The name of the routine.
    interval : int
        The interval at which the routine runs.
    unit : str
        The unit of time for the interval.
    priority : int
        The priority level of the routine.
    steps : List[Step]
        The list of steps within the routine.
    error_contacts : List[str]
        List of error contacts for notification.
    completion_contacts : List[str]
        List of completion contacts for notification.
    """

    def __init__(
        self,
        name: str,
        interval: int,
        unit: str,
        priority: int,
        steps: List[Step],
        error_contacts: Optional[List[str]] = None,
        completion_contacts: Optional[List[str]] = None,
    ):
        self.name = name
        self.interval = interval
        self.unit = unit
        self.priority = priority
        self.steps = steps
        self.error_contacts = error_contacts if error_contacts is not None else []
        self.completion_contacts = (
            completion_contacts if completion_contacts is not None else []
        )
        self.error_reports: List[Dict[str, str]] = []
        self.errors: List[bool | Exception] = []
        self.run_times: List[int | float] = []

    @property
    def run_time(self) -> dt.timedelta:
        return self.start_dt - self.stop_dt

    def reset(self):
        """_summary_"""
        self.error_reports = []
        self.errors = []
        self.run_times = []

    def __str__(self) -> str:
        """
        Get a string representation of the routine for notifications/error reporting.

        Returns
        -------
        str
            A string describing the routine and its steps.
        """
        header = f"Routine: {self.name} runs every {self.interval} {self.unit}"
        steps = [f"Step {i}: {s}" for i, s in enumerate(self.steps)]
        body = "\n".join(steps)
        return header + "\nSteps:\n" + body

    def get_err_report(self, error: Exception) -> Dict[str, str]:
        """_summary_

        Parameters
        ----------
        error : Exception
            _description_
        routine : Routine
            _description_

        Returns
        -------
        Dict[str, str]
            _description_
        """
        title = f"{self.name}: {error.__class__.__name__}"
        body = str(error)
        return {"title": title, "body": body}

    def _run(
        self,
        dispenser: Dispenser,
        monitor: Monitor,
    ) -> Optional[CancelJob]:
        self.start_dt = dt.datetime.now()
        stop = False
        job_ret = None
        for step in self.steps:
            ret = dispenser.run_step(step, monitor)

            run_time, errs = ret
            self.errors.append(errs)
            self.run_times.append(run_time)

            # Case where an initial state error was reported.
            if run_time == 0:
                if step.report_invalid_start:
                    self.error_reports.append(self.get_err_report(errs[0]))
                if not (step.proceed_on_invalid_start):
                    stop = True

            # Case where the initial state was correctly met
            elif run_time > 0:
                # Report and log each individual error encountered.
                for e in errs:
                    self.error_reports.append(self.get_err_report(e))

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
        self,
        dispenser: Dispenser,
        monitor: Monitor,
    ) -> Optional[CancelJob]:
        """_summary_

        Parameters
        ----------
        dispenser : Dispenser
            _description_
        monitor : Monitor
            _description_

        Returns
        -------
        Optional[CancelJob]
            _description_
        """
        job_ret = self._run(dispenser=dispenser, monitor=monitor)
        self.stop_dt = dt.datetime.now()
        return job_ret
