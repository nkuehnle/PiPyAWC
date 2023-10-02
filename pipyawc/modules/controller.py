# Default module imports
import datetime as dt
from pathlib import Path
from typing import Dict, List, Union, Any, Optional

# Third-party module imports
import pandas as pd

# Custom module imports
# Control high-lvl logic, schedule, user input & more
from .operations import (
    Messenger,
    AScheduler,
    RemoteCommand,
    CancelJob,
)
from .operations import MessengerError

# Interact w/ RPi GPIO headers/equipment
from .peripherals import (
    Monitor,
    Routine,
    Dispenser,
)
from .peripherals import ErrorSensorTriggered, PumpTimeoutError

TIME_FMT = "%m/%d/%Y: %H:%M:%S"

HOME_DIR = Path(__file__).parents[1]
LOG_DIR = HOME_DIR / "data" / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=False)
except FileExistsError:
    pass


class Controller:
    def __init__(
        self,
        messenger: Messenger = Messenger(),
        message_check_delay_s: int = 30,
        routines: Dict[str, Routine] = {},
        monitor: Monitor = Monitor(),
        dispenser: Dispenser = Dispenser(),
        schedule: AScheduler = AScheduler(),
    ):
        """
        Initialize the Controller.

        Parameters
        ----------
        messenger : Messenger, optional
            The messenger used for notifications, by default Messenger()
        message_check_delay_s : int, optional
            The delay in seconds for checking message commands, by default 30
        routines : Dict[str, Routine], optional
            A dictionary of routines, by default {}
        monitor : Monitor, optional
            The monitor for monitoring routines, by default Monitor()
        dispenser : Dispenser, optional
            The dispenser for dispensing, by default Dispenser()
        schedule : AScheduler, optional
            The scheduler for routines, by default AScheduler()
        """
        self.messenger = messenger
        self.routines = routines
        self.monitor = monitor
        self.dispenser = dispenser
        self.schedule = schedule
        self.message_check_delay_s = message_check_delay_s
        self.pending_commands: List[RemoteCommand] = []

        check_job = self.schedule.every(self.message_check_delay_s).seconds
        check_job.do(self.check_orders)

    @property
    def current_schedule(self) -> str:
        """
        Get the current schedule.

        Returns
        -------
        str
            A string representation of the current schedule.
        """
        job_strs = []

        for job in self.schedule.jobs:
            if not (any(["Update " in tag for tag in job.tags])):
                job_strs.append(job.to_string(TIME_FMT))

        return "\n".join(job_strs)

    def register_routine(self, routine: Routine):
        """
        Register a routine.

        Parameters
        ----------
        routine : Routine
            The routine (dataclass representation) to register.
        """
        name = routine.name
        print(f"Registering {name}")
        self.routines[name] = routine

        if routine.interval is not None:
            job = self.schedule.every(routine.interval)
            job.unit = routine.unit
            job.priority = routine.priority
            job.tag(name)
            job.tag("Repeating")
            job.do(self.run_routine, name=name)

    def run_routine(self, name: str) -> Optional[CancelJob]:
        """
        Run a routine.

        Parameters
        ----------
        name : str
            The name of the routine to run (must be registered already).

        Returns
        -------
        Optional[CancelJob]
            The cancellation job, if applicable.
        """
        routine = self.routines[name]

        start_dt = dt.datetime.now().strftime(TIME_FMT)
        stop = False

        errors = []
        run_times: List[float] = []
        job_ret = None  # Only changed if the job should cancel on errors.
        error_reports = []

        for step in routine.steps:
            ret = self.dispenser.run_step(step, self.monitor)

            run_time, errs = ret
            errors.append(errs)
            run_times.append(run_time)

            # Case where an initial state error was reported.
            if run_time == 0:
                if step.report_invalid_start:
                    subject = f"{routine.name}: {ret.__class__.__name__}"
                    body = str(errs[0])
                    error_reports.append({"subject": subject, "body": body})
                if not (step.proceed_on_invalid_start):
                    stop = True

            # Case where the initial state was correctly met
            elif run_time > 0:
                # Report and log each individual error encountered.
                for e in errs:
                    subject = f"{routine.name}: {e.__class__.__name__}"
                    body = str(e)
                    error_reports.append({"subject": subject, "body": body})

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

        # Log results and notify user of status.
        self.log_run(
            name=routine.name, run_times=run_times, errors=errors, start_dt=start_dt
        )

        if any(error_reports):
            for r in error_reports:
                self.notify(routine.error_contacts, **r)

        if isinstance(job_ret, CancelJob):
            subject = f"{routine.name}: Critical Error!"
            body = (
                f"A scheduled job ({routine.name}) was canceled due to a critical "
                "error!"
            )
        else:
            subject = f"{routine.name}: Complete!"
            body = f"A job started at {start_dt} finished running!"

        self.notify(routine.completion_contacts, body, subject)

        return job_ret

    def log_run(
        self,
        name: str,
        run_times: List[float],
        errors: List[List[Union[bool, Exception]]],
        start_dt: str,
    ):
        """
        Log the run details of a routine.

        Parameters
        ----------
        name : str
            The name of the routine.
        run_times : List[float]
            The list of run times.
        errors : List[List[Union[bool, Exception]]]
            The list of errors encountered during the run.
        start_dt : str
            The start date and time.
        """
        routine_dir = LOG_DIR / name.replace(" ", "_")

        try:
            routine_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            pass

        logs = zip(run_times, errors)  # Zip these for looping

        for i, log in enumerate(logs):  # Index, run_time, step errors(s)
            time, errs = log[0], log[1]
            step_name = self.routines[name].steps[i].name.replace(" ", "_")
            log_file = routine_dir / f"{step_name}.csv"

            err_dict: Dict[str, List[Any]] = {"timeout": [False]}

            if any(errs):
                for e in errs:
                    if isinstance(e, ErrorSensorTriggered):
                        err_dict[f"{e.name}_error"] = [e.remaining_runs]
                    if isinstance(e, PumpTimeoutError):
                        err_dict["timeout"] = [True]

            if time is not None:
                new_row = {"run_time": [time]}
                new_row.update(err_dict)
                new_df = pd.DataFrame(new_row, index=[start_dt])

                if log_file.is_file() and log_file.exists():
                    existing_df = pd.read_csv(log_file, sep=",", index_col=0)
                    new_df = pd.concat([existing_df, new_df])

                new_df.to_csv(
                    log_file, sep=",", index=True, header=True, index_label="Start Time"
                )

    def notify(self, recipients: List[str], body: str, subject: str = "") -> CancelJob:
        """
        Send notifications using the Messenger.

        This function wraps the Messenger's send method and handles exceptions.
        It helps ensure that messenger connection issues do not crash the program
        and emails are re-scheduled if not successfully sent.

        Parameters
        ----------
        recipients : List[str]
            A list of recipients for the notification.
        body : str
            The body of the notification.
        subject : str, optional
            The subject of the notification, by default ''.

        Returns
        -------
        CancelJob
            The cancellation job, if applicable.
        """
        kwargs: Dict[str, Union[str, List[str]]] = {
            "body": body,
            "subject": subject,
        }
        if any(recipients):
            try:
                self.messenger.send(recipients=recipients, **kwargs)
            except MessengerError:  # Re-schedules w/ low priority
                kwargs.update({"recipients": recipients})
                try_again = self.schedule.every(1).minute
                try_again.lowest_priority
                try_again.run_once = True
                try_again.tag(f"Notify {recipients}")
                try_again.do(self.notify, **kwargs)

            return CancelJob()

    def check_orders(self) -> CancelJob:
        """
        Check for pending orders using the Messenger.

        This function is passed to PJob.do() and catches connection-related errors.

        Returns
        -------
        CancelJob
            The cancellation job, if applicable.
        """
        try:
            self.pending_commands += self.messenger.check()
        except Exception as e:  # MessengerError as e: # Re-schedules w/ low priority
            print(f"Message check error: {e}")
