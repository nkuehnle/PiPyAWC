# Built-in modules
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import datetime as dt

# Third-party module imports
import numpy as np

HOME_DIR = Path(__file__).parents[3]
LOG_DIR = HOME_DIR / "data" / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=False)
except FileExistsError:
    pass


@dataclass
class Step:
    """
    Represents a step within a routine.

    Parameters
    ----------
    name : str
        The name of the step.
    pump : str
        The pump associated with the step.
    start_states : List[str]
        The list of start states for the step.
    end_states : List[str]
        The list of end states for the step.
    error_checks : List[str]
        Tuple of error checks for the step.
    max_runtime : float
        The maximum allowed runtime for the step.
    parent : Optional[Routine], optional
        The parent routine this step belongs to, by default None.
    first_run : Optional[dt.datetime], optional
        The datetime of the first run, by default None.
    report_invalid_start : bool, optional
        Whether to report an invalid start, by default True.
    proceed_on_invalid_start : bool, optional
        Whether to proceed on an invalid start, by default False.
    proceed_on_timeout : bool, optional
        Whether to proceed on timeout, by default False.
    proceed_on_error : bool, optional
        Whether to proceed on error, by default False.
    cancel_on_critical_failure : bool, optional
        Whether to cancel on a critical failure, by default True.

    Methods
    -------
    __str__()
        Get a string representation of the step.
    max_time()
        Get the maximum allowed runtime for the step.
    min_time()
        Get the minimum allowed runtime for the step.
    interval_range()
        Get the runtime interval range for the step.

    Attributes
    ----------
    name : str
        The name of the step.
    pump : str
        The pump associated with the step.
    start_states : List[str]
        The list of start states for the step.
    end_states : List[str]
        The list of end states for the step.
    error_checks : List[str]
        Tuple of error checks for the step.
    max_runtime : float
        The maximum allowed runtime for the step.
    parent : Optional[Routine]
        The parent routine this step belongs to.
    first_run : Optional[dt.datetime]
        The datetime of the first run.
    report_invalid_start : bool
        Whether to report an invalid start.
    proceed_on_invalid_start : bool
        Whether to proceed on an invalid start.
    proceed_on_timeout : bool
        Whether to proceed on timeout.
    proceed_on_error : bool
        Whether to proceed on error.
    cancel_on_critical_failure : bool
        Whether to cancel on a critical failure.
    """

    name: str
    pump: str
    start_states: List[str]
    end_states: List[str]
    error_checks: List[str]
    max_runtime: float
    parent: Optional["Routine"] = None
    first_run: Optional[dt.datetime] = None
    report_invalid_start: bool = True
    proceed_on_invalid_start: bool = False
    proceed_on_timeout: bool = False
    proceed_on_error: bool = False
    cancel_on_critical_failure: bool = True

    def __str__(self) -> str:
        """
        Get a string representation of the step for notifications/error reporting.

        Returns
        -------
        str
            A string describing the step.
        """
        x = (
            f"{self.name} ({self.start_states} to {self.end_states};"
            + f"runtime = {self.min_time:.2f}-{self.max_time:.2f} seconds)"
        )
        return x

    @property
    def max_time(self) -> float:
        """
        Get the maximum allowed runtime for the step.

        Returns
        -------
        float
            The maximum allowed runtime.
        """
        return self.interval_range().max()

    @property
    def min_time(self) -> float:
        """
        Get the minimum allowed runtime for the step.

        Returns
        -------
        float
            The minimum allowed runtime.
        """
        return self.interval_range().min()

    def interval_range(self) -> np.ndarray:
        """
        Get the runtime interval range for the step.

        Returns
        -------
        np.ndarray
            An array representing the runtime interval range.
        """
        return np.array([0.0, self.max_runtime])


@dataclass
class Routine:
    """
    Represents a routine consisting of multiple steps.

    Parameters
    ----------
    name : str
        The name of the routine.
    run_time_confidence : float
        The confidence level for runtime predictions.
    interval : int
        The interval at which the routine runs.
    unit : str
        The unit of time for the interval (e.g., 'minutes', 'hours').
    priority : int
        The priority level of the routine.
    steps : List[Step]
        The list of steps within the routine.
    error_contacts : List[str], optional
        List of error contacts for notification, by default [].
    completion_contacts : List[str], optional
        List of completion contacts for notification, by default [].

    Methods
    -------
    __str__()
        Get a string representation of the routine.

    Attributes
    ----------
    name : str
        The name of the routine.
    run_time_confidence : float
        The confidence level for runtime predictions.
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

    name: str
    run_time_confidence: float
    interval: int
    unit: str
    priority: int
    steps: List[Step]
    error_contacts: List[str] = []
    completion_contacts: List[str] = []

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
