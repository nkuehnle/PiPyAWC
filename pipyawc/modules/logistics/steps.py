import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Union

if TYPE_CHECKING:
    from .routines import Routine


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
    end_states : error_checks: Tuple[str]
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
        return max(self.interval_range())

    @property
    def min_time(self) -> float:
        """
        Get the minimum allowed runtime for the step.

        Returns
        -------
        float
            The minimum allowed runtime.
        """
        return min(self.interval_range())

    def interval_range(self) -> List[Union[int, float]]:
        """
        Get the runtime interval range for the step.

        Returns
        -------
        List[int | float]
            A list representing the runtime interval range.
        """
        return [0.0, self.max_runtime]
