import inspect
from typing import Dict, List, Optional

from .logistics import Routine
from .peripherals import Dispenser, Monitor  # Interact w/ RPi GPIO headers/equipment
from .services import (  # Control high-lvl logic, schedule, user input & more
    AdvJob,
    AdvScheduler,
    CancelJob,
    Messenger,
    NotificationFailure,
    NotifyType,
    RemoteCommand,
)
from .run_routine import run

TIME_FMT = "%m/%d/%Y: %H:%M:%S"


class Controller:
    """_summary_"""

    def __init__(
        self,
        messenger: Messenger,
        routines: Dict[str, Routine] = {},
        monitor: Monitor = Monitor(),
        dispenser: Dispenser = Dispenser(),
        schedule: AdvScheduler = AdvScheduler(),
    ):
        """
        Initialize the Controller.

        Parameters
        ----------
        messenger : messenger
            The messenger used for notifications.
        routines : Dict[str, Routine], optional
            A dictionary of routines, by default {}
        monitor : Monitor, optional
            The monitor for monitoring routines, by default Monitor()
        dispenser : Dispenser, optional
            The dispenser for dispensing, by default Dispenser()
        schedule : AdvScheduler, optional
            The scheduler for routines, by default AdvScheduler()
        """
        self.messenger = messenger
        self.routines = routines
        self.monitor = monitor
        self.dispenser = dispenser
        self.schedule = schedule
        self.pending_commands: List[RemoteCommand] = []

        check_job = self.schedule.every(self.messenger.check_delay_sec).seconds
        check_job.do(self.check_orders)

    @property
    def jobs(self) -> List[AdvJob]:
        """_summary_

        Returns
        -------
        List[AdvJob]
            _description_
        """
        return self.schedule.jobs

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

        for job in self.jobs:
            if not (any(["Update " in str(tag) for tag in job.tags])):
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
            job.do(self.run, name=name)

    def run(self, name: str) -> Optional[CancelJob]:
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
        job_ret = run(routine=routine, dispenser=self.dispenser, monitor=self.monitor)
        for r in routine.error_reports:
            self.notify(
                contacts=routine.error_contacts,
                notify_type=NotifyType.FAILURE,
                **r,
            )

        if isinstance(job_ret, CancelJob):
            title = f"{routine.name}: Critical Error!"
            body = (
                f"A scheduled job ({routine.name}) was canceled due to a critical "
                + "error!"
            )
            notice_type = NotifyType.FAILURE
        else:
            title = f"{routine.name}: Complete!"
            started_at = routine.start_dt.strftime(TIME_FMT)
            runtime = int(routine.run_time.total_seconds())
            body = (
                f"A job started at {started_at} finished running in {runtime} seconds!"
            )
            notice_type = NotifyType.SUCCESS

        self.notify(
            body=body,
            title=title,
            contacts=routine.completion_contacts,
            notify_type=notice_type,
        )

        routine.reset()

        return job_ret

    def notify(
        self,
        title: str,
        body: str,
        contacts: List[str],
        notify_type: NotifyType,
    ) -> CancelJob:
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
        contacts = [c for c in contacts if c in self.messenger.contacts.keys()]
        if any(contacts):
            try:
                self.messenger.notify(
                    body=body,
                    title=title,
                    contacts=contacts,
                    notify_type=notify_type,
                )
            except NotificationFailure:
                params = inspect.signature(self.notify).parameters
                kwargs = {k: v for k, v in locals().items() if k in params}
                try_again = self.schedule.every(1).minute
                try_again.lowest_priority
                try_again.run_once = True
                try_again.tag(f"Notify {contacts}")
                try_again.do(self.notify, **kwargs)

        return CancelJob()

    def check_orders(self):
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
