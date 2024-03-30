# Default module imports
import random
import string
from typing import Any, List, Optional, Set

from schedule import CancelJob, Job, Scheduler


class AdvancedScheduler(Scheduler):
    def __init__(self) -> None:
        """
        A subclass of the factory :class: 'Scheduler' which overloads the
        method :meth: 'Scheduler.every()' to return instances of :class:
        'AdvancedJob' instead.

        Objects instantiated by the :class: `AdvancedScheduler` are
        factories to create jobs, keep record of scheduled jobs and handle
        their execution.
        """
        super().__init__()
        self.jobs: List["AdvancedJob"] = self.jobs  # type: ignore[assignment]

    def get_jobs_from_tags(self, tags: List[str]) -> List["AdvancedJob"]:
        """Get any/all jobs that include all of the provided tags.

        Parameters
        ----------
        tags : List[str]
            A list of hashable tags

        Returns
        -------
        List[AdvancedJob]
            A list of PJob instances with matching tags
        """
        jobs: List[Set[AdvancedJob]] = []
        for tag in tags:
            _jobs: List[AdvancedJob] = self.get_jobs(tag)  # type: ignore[assignment]
            jobs.append(set(_jobs))

        job_set = jobs[0].intersection(*jobs[1:])

        return list(job_set)

    def every(self, interval: int = 1) -> "AdvancedJob":
        """Schedule a new periodic job.

        Parameters
        ----------
        interval : int, optional
            A quantity of a certain time unit, by default 1

        Returns
        -------
        AdvancedJob
            An unconfigured AdvancedJob instance
        """
        job = AdvancedJob(interval, self)
        job.random_tag()
        return job


class AdvancedJob(Job):
    def __init__(
        self,
        interval: int,
        scheduler: AdvancedScheduler,
        priority: int = 0,
        run_once=False,
    ):
        """
        A subclass of the periodic job class Job as used by the AdvancedScheduler class

        Every job runs at a given fixed time interval that is defined by:
            * a time unit, set by a method wrapped as a propery i.e. AdvancedJob.seconds
            * a quantity of time units defined by the interval attribute

        A job is usually created and returned by the method AdvancedScheduler.every,
        which also defines its interval, i.e. AdvancedScheduler.every(5).seconds

        This subclass overloads Job.__lt__() to check the 'priority' in the event that
        two jobs are scheduled for the same time.

        Default behavior

        It also implements a AdvancedJob.random_tag() method for disambiguating
        otherwise similarly-tagged jobs, i.e. for cancellation.

        Parameters
        ----------
        interval : int
            A quantity of a certain time unit
        scheduler : AdvancedScheduler
            The AdvancedScheduler instance that this job will register itself with once
            it has been fully configured in Job.do(). Returns an error if missing
            when do() is called.
        priority : int, optional
            The priority of the job (lower value -> higher priority),
            by default 0 (max priority)
        """
        super().__init__(interval, scheduler)
        assert scheduler is not None
        self.scheduler: AdvancedScheduler = scheduler
        self.priority = priority
        self.run_once = run_once

    @property
    def competing_jobs(self) -> List["AdvancedJob"]:
        """_summary_

        Returns
        -------
        _type_
            _description_
        """
        jobs: List[AdvancedJob] = self.scheduler.jobs  # type: ignore[assignment]
        return jobs

    def __lt__(self, other: Job) -> bool:
        """
        In the standard schedule module, PeriodicJobs are sortable based on
        the scheduled time they run next. In this implementation, a priority
        can be set which is checked in the event that two jobs happen at the
        same time.
        """
        if (other.next_run is None) and (self.next_run is None):
            return False
        elif (other.next_run is None) and (self.next_run is not None):
            return True
        elif (other.next_run is not None) and (self.next_run is None):
            return False

        assert self.next_run is not None
        assert other.next_run is not None

        if self.next_run != other.next_run:
            return self.next_run < other.next_run
        else:
            if isinstance(other, AdvancedJob):
                return self.priority < other.priority
            else:
                return self.next_run < other.next_run

    @property
    def highest_priority(self):
        """
        Set job to the highest priority among all jobs associated with the
        parent schedule
        """
        priorities = [j.priority for j in self.competing_jobs]
        self.priority = min(priorities) - 1

    @property
    def lowest_priority(self):
        """
        Set job to the lowest priority among all jobs associated with the
        parent schedule
        """
        priorities = [j.priority for j in self.competing_jobs]
        self.priority = max(priorities) + 1

    def random_tag(self, k: int = 5) -> None:
        """
        Adds a random string of k letters/digits as a tag to the job's tag set.

        Useful for disambiguating jobs that are otherwise similarly tagged.

        Parameters
        ----------
        k : int
            [description]
        """
        t = "".join(random.choices(string.ascii_uppercase + string.digits, k=k))
        self.tags.add(t)

    def to_string(self, dt_fmt: Optional[str] = None) -> str:
        """[summary]

        Parameters
        ----------
        dt_fmt : Optional[str], optional
            [description], by default None

        Returns
        -------
        str
            [description]
        """
        tags = ", ".join([str(t) for t in self.tags])
        if (dt_fmt is not None) and (self.next_run is not None):
            return tags + " @ " + self.next_run.strftime(dt_fmt)
        else:
            return tags

    def run(self) -> Any:
        """
        Run the job and immediately reschedule it.
        If the job's deadline is reached (configured using .until()), the job is not
        run and CancelJob is returned immediately. If the next scheduled run exceeds
        the job's deadline, CancelJob is returned after the execution. In this latter
        case CancelJob takes priority over any other returned value.

        Returns
        -------
        Any
            The return value returned by the `job_func`, or CancelJob if the job's
            deadline is reached.
        """
        ret = super().run()
        if self.run_once:
            return CancelJob()
        else:
            return ret

    def cancel(self):
        """Cancels the current job"""
        if self.next_run is not None:
            self.scheduler.cancel_job(self)
