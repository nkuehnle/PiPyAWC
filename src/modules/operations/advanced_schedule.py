# Default module imports
import string
import random
from typing import List, Optional
# Third-party nodule imports
try:
    from schedule import Scheduler, Job, CancelJob
except ModuleNotFoundError as e:
    print(f"WARNING: please run pip install schedule")
    raise e

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


    def get_jobs_from_tags(self, tags: List[str]) -> List[Job]:
        """
        Get any/all jobs that include all of the provided tags.
        
        :param tags: A list of hashable tags
        :reurn: A list of PJob instances with matching tags
        """
        jobs = []
        for tag in tags:
            jobs.append(set(self.get_jobs(tag)))

        jobs = jobs[0].intersection(*jobs[1:])

        return list(jobs)

    def every(self, interval: int = 1) -> 'AdvancedJob':
        """
        Schedule a new periodic job.

        :param interval: A quantity of a certain time unit
        :return: An unconfigured :class:`AdvancedJob <AdvancedJob>`
        """
        job = AdvancedJob(interval, self)
        job.random_tag()
        return job

class AdvancedJob(Job):
    def __init__(self, interval: int, scheduler: AdvancedScheduler = None,
                 priority: int = 0, run_once = False):
        """
        A subclass of the periodic job class :class: 'Job' as used by 
        :class:`AdvancedScheduler'
            
        Every job runs at a given fixed time interval that is defined by:

        * a :meth:`time unit <Job.second>`
        * a quantity of `time units` defined by `interval`

        A job is usually created and returned by 
        :meth:`AdvancedScheduler.every` method, which also defines its
        `interval`

        This subclass overloads :meth: Job.__lt__() to check the 'priority'
        in the event that two jobs are scheduled for the same time.

        Default behavior 

        It also implements a :meth: AdvancedJob.random_tag() for
        disambiguating otherwise similarly-tagged jobs, i.e. for cancellation.

        Parameters
        ----------
        interval : int
            A quantity of a certain time unit
        scheduler : AdvancedScheduler, optional
            The :class:`AdvancedScheduler <AdvancedScheduler>` instance
            that this job will register itself with once it has been fully
            configured in :meth:`Job.do()`
        priority : int, optional
            The priority of the job (lower value -> higher priority), by
            default 0 (max priority)
        """
        super().__init__(interval, scheduler)
        self.priority = priority
        self.run_once = run_once
    
    def __lt__(self, other: Job) -> bool:
        """
        In the standard schedule module, PeriodicJobs are sortable based on 
        the scheduled time they run next. In this implementation, a priority 
        can be set which is checked in the event that two jobs happen at the
        same time.
        """
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
        jobs = self.scheduler.jobs
        priorities = [j.priority for j in  jobs if hasattr(j, 'priority')]
        self.priority = min(priorities) - 1

    @property
    def lowest_priority(self):
        """
        Set job to the lowest priority among all jobs associated with the
        parent schedule
        """
        jobs = self.scheduler.jobs
        priorities = [j.priority for j in  jobs if hasattr(j, 'priority')]
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
        t = ''.join(random.choices(string.ascii_uppercase + string.digits, k=k))
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
        tags = ', '.join(self.tags)
        if dt_fmt != None:
            return tags+' @ '+self.next_run.strftime(dt_fmt)
        else:
            return tags

    def run(self):
        """
        Run the job and immediately reschedule it.
        If the job's deadline is reached (configured using .until()), the job is not
        run and CancelJob is returned immediately. If the next scheduled run exceeds
        the job's deadline, CancelJob is returned after the execution. In this latter
        case CancelJob takes priority over any other returned value.

        :return: The return value returned by the `job_func`, or CancelJob
            if the job's deadline is reached.
        """
        ret = super().run()
        if self.run_once == True:
            return CancelJob()
        else:
            return ret