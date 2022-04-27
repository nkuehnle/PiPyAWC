# Default module imports
import datetime as dt
from pathlib import Path
from typing import Dict, List, Union, Type
import socket
import imaplib
# Third-party module imports
try:
    from imap_tools import ImapToolsError, MailMessage
except ModuleNotFoundError as e:
    print(f"WARNING: please run pip install imap-tools")
    raise e
import pandas as pd
from statsmodels.formula.api import ols
from statsmodels.stats.api import DescrStatsW as dsw
from statsmodels.regression.linear_model import RegressionResults as RR
from statsmodels.stats.weightstats import DescrStatsW as DSW
# Custom module imports
from .operations import *  # Control high-lvl logic, schedule, user input & more
from .peripherals import *  # Interact w/ RPi GPIO headers/equipment

TIME_FMT = '%m/%d/%Y: %H:%M:%S'

HOME_DIR = Path(__file__).parents[1]
LOG_DIR = HOME_DIR / 'data' / 'logs'
try:
    LOG_DIR.mkdir(parents=True, exist_ok=False)
except FileExistsError:
    pass

class Controller:
    def __init__(
        self,
        messenger: Messenger,
        routine_update_interval: int,
        routine_update_unit: str,
        email_check_delay_s: int,
        routines: Dict[str, Routine] = {},
        monitor: Monitor = Monitor(),
        dispenser: Dispenser = Dispenser(), 
        schedule: AScheduler = AScheduler()
        ):
        self.messenger = messenger
        self.routines = routines
        self.monitor = monitor
        self.dispenser = dispenser
        self.schedule = schedule
        self.routine_update_interval = routine_update_interval
        self.routine_update_unit =  routine_update_unit
        self.email_check_delay_s = email_check_delay_s
        self.pending_commands: List[MailMessage] = []

        check_job = self.schedule.every(self.email_check_delay_s).seconds
        check_job.do(self.check_orders)


    @property
    def current_schedule(self) -> str:
        """[summary]

        Returns
        -------
        str
            [description]
        """
        job_strs = []
        
        for job in self.schedule.jobs:
            if not(any(['Update ' in tag for tag in job.tags])):
                job_strs.append(job.to_string(TIME_FMT))

        return '\n'.join(job_strs)

    def register_routine(self, routine: Routine):
        """[summary]

        Parameters
        ----------
        routine : Routine
            [description]
        """
        name = routine.name
        print(f"Registering {name}")
        self.routines[name] = routine

        if routine.interval != None:
            job = self.schedule.every(routine.interval)
            job.unit = routine.unit
            job.priority = routine.priority
            job.tag(name)
            job.tag('Repeating')
            job.do(self.run_routine, name=name)

            # Schedule updater
            update_job = self.schedule.every(self.routine_update_interval)
            getattr(update_job, self.routine_update_unit)
            update_job.do(self.update_routine, name=name)
            update_job.tag(f'Update {name}')

    def _update_step(self, step: Step, log_path: Path) -> Union[RR, DSW, Type[None]]:
        """[summary]

        Parameters
        ----------
        step : Step
            [description]
        log_path : Path
            [description]

        Returns
        -------
        Union[RegressionResults, DescrStatsW, Type[None]]
            [description]
        """
        step_df = pd.read_csv(log_path, sep=',', index_col=0)
        step_df.index = pd.to_datetime(step_df.index, format=TIME_FMT)
        step.first_run = step_df.index.min()

        if len(step_df) >= 30:
            step_df['timedelta'] = (step_df.index - step.first_run).dt.seconds
            comparison_str = f"run_time ~ {'run_time'}"
            model = ols(comparison_str, step_df).fit()
        elif 30 > len(step_df) >= 5:
            model = dsw(step_df['run_time'])
        else:
            model = None
        return model


    def update_routine(self, name: Union[str, Routine]):
        """[summary]

        Parameters
        ----------
        name : Union[str, Routine]
            [description]
        """
        routine_dir = LOG_DIR / name.replace(' ', '_')
        routine = self.routines[name]

        for s in routine.steps:
            sname = s.name.replace(' ', '_')
            log_path = routine_dir / f'{sname}.csv'
            if log_path.is_file() and log_path.exists():
                s._model = self._update_step(s, log_path)
            else:
                s._model = None

    def run_routine(self, name: Union[str, Routine]):
        """[summary]

        Parameters
        ----------
        name : Union[str, Routine]
            [description]

        Returns
        -------
        [type]
            [description]
        """
        routine = self.routines[name]

        start_dt = dt.datetime.now().strftime(TIME_FMT)
        stop = False

        errors = []
        run_times = []
        job_ret = None # Only changed if the job should cancel on errors.
        error_reports = []

        for step in routine.steps:
            ret = self.dispenser.run_step(step, self.monitor)

            # Case where an initial state error was reported.
            if isinstance(ret, InitialStateError):
                errors.append([])
                run_times.append(None)

                if step.report_invalid_start:
                    subject = f'{routine.name}: {ret.__class__.__name__}'
                    body = str(ret)
                    error_reports.append({'subject': subject, 'body': body})
                if not(step.proceed_on_invalid_start):
                    stop = True

            # Case where one or more mid-run errors were reported.
            elif isinstance(ret, tuple):
                run_time, errs = ret
                errors.append(errs)
                run_times.append(run_time)
                # Report and log each individual error encountered.
                for e in errs:
                    subject = f'{routine.name}: {e.__class__.__name__}'
                    body = str(e)
                    error_reports.append({'subject': subject, 'body': body})

                    if isinstance(e, PumpTimeoutError):
                        if not(step.proceed_on_timeout):
                            stop = True
                    elif isinstance(e, ErrorSensorTriggered):
                        final_run = e.remaining_runs <= 0
                        if not(step.proceed_on_error) and final_run:
                            stop = True
            
            # Case where the step ran normally
            else:
                run_times.append(ret)
                errors.append([])

            # If we need to stop early...
            if stop == True:
                if step.cancel_on_critical_failure:
                    job_ret = CancelJob()
                break # End for loop early
        
        # Log results and notify user of status.
        self.log_run(routine.name, run_times, errors, start_dt)

        if any(error_reports):
            for r in error_reports:
                self.notify(routine.error_contacts, **r)

        if isinstance(job_ret, CancelJob):
            subject = f'{routine.name}: Critical Error!'
            body = f'A scheduled job was canceled due to a critical error!'
        else:
            subject = f'{routine.name}: Complete!'
            body = f'A job started at {start_dt} finished running!'

        self.notify(routine.completion_contacts, body, subject)
        return job_ret


    def log_run(self, name: str, run_times: List[float],
            errors: List[Union[Exception, None]], start_dt: str):
        """[summary]

        Parameters
        ----------
        name : str
            [description]
        run_times : List[float]
            [description]
        errors : List[Union[Exception, None]]
            [description]
        start_dt : str
            [description]
        """
        routine_dir = LOG_DIR / name.replace(' ','_')

        try:
            routine_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            pass

        logs = zip(run_times, errors) # Zip these for looping

        for i, (time, errs) in enumerate(logs): # Index, run_time, step errors(s)
            step_name = self.routines[name].steps[i].name.replace(' ','_')
            log_file = routine_dir / f'{step_name}.csv'

            err_dict = {'timeout': [False]}

            if any(errs):
                for e in errs:
                    if isinstance(e, ErrorSensorTriggered):
                        err_dict[f'{e.name}_error'] = [e.remaining_runs]
                    if isinstance(e, PumpTimeoutError):
                        err_dict['timeout'] = [True]
                        
            if time != None:
                new_row = {'run_time': [time]}
                new_row = {**new_row, **err_dict}
                new_df = pd.DataFrame(new_row, index=[start_dt])

                if log_file.is_file() and log_file.exists():
                    existing_df = pd.read_csv(log_file, sep=',')
                    new_df =  pd.concat([existing_df, new_df,], join='outer', axis=0)
                    
                new_df.to_csv(log_file, sep=',')


    def notify(self, recipients: List[str], body: str,
               subject: str = '') -> CancelJob:
        """Wraps :meth: 'Messenger.send()'

        This is the function that is passed to :meth: AJob.do() if an 
        exception occurs.

        Helps ensure that messenger connection issues do not crash the program
        & emails are re-scheduled if not successfully sent.

        Parameters
        ----------
        recipients : List[str]
            [description]
        body : str
            [description]
        subject : str, optional
            [description], by default ''

        Returns
        -------
        CancelJob
            [description]
        """
        kwargs = {'recipients': recipients, 'body': body, 'subject': subject}
        if any(recipients):
            try:
                self.messenger.send(**kwargs)
            except (ImapToolsError, socket.gaierror) as e: # Re-schedules w/ low priority
                try_again = self.schedule.every(1).minute
                try_again.lowest_priority
                try_again.run_once = True
                try_again.tag(f'Notify {recipients}')
                try_again.do(self.notify, **kwargs)

            return CancelJob()


    def check_orders(self) -> CancelJob:
        """Wraps :meth: 'Messenger.check()'

        This function is passed to :meth: PJob.do() and catches
        connection-related errors.
        """
        exceptions = (ImapToolsError, socket.gaierror, imaplib.IMAP4.abort)
        try:
            new_messages = self.messenger.check()
            self.pending_commands += new_messages
        except exceptions as e: # Re-schedules w/ low priority
            print(f'Email check error: {e}')