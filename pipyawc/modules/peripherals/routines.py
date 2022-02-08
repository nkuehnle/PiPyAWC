from dataclasses import dataclass
from typing import Tuple, List, Union
from pathlib import Path
import datetime as dt
# Third-party module imports
import pandas as pd
import numpy as np
from statsmodels.regression.linear_model import RegressionResults
from statsmodels.stats.weightstats import DescrStatsW

HOME_DIR = Path(__file__).parents[3]
LOG_DIR = HOME_DIR / 'data' / 'logs'
try:
    LOG_DIR.mkdir(parents=True, exist_ok=False)
except FileExistsError:
    pass

@dataclass
class Step:
    name: str
    pump: str
    start_state: str
    end_state: str
    error_checks: Tuple[str]
    initial_max_runtime: float
    parent: 'Routine' = None
    first_run: dt.datetime = None
    report_invalid_start: bool = True
    proceed_on_invalid_start: bool = False
    proceed_on_timeout: bool = False
    proceed_on_error: bool = False
    cancel_on_critical_failure: bool = True
    # Not to be set by user
    _model: Union[RegressionResults, DescrStatsW] = None

    def __str__(self):
        x = f'{self.name} ({self.start_state} to {self.end_state};' + \
            f'runtime = {self.min_time:.2f}-{self.max_time:.2f} seconds)'
        return x

    @property
    def max_time(self):
        return self.interval_range(dt.datetime.now()).max()

    @property
    def min_time(self):
        return self.interval_range(dt.datetime.now()).min()

    def interval_range(self, start_dt: dt.datetime) -> np.ndarray:
        """[summary]

        Parameters
        ----------
        start_dt : dt.datetime
            [description]
        monitor : Monitor
            [description]

        Returns
        -------
        np.ndarray
            [description]
        """
        alpha = self.parent.run_time_confidence
        
        if isinstance(self._model, DescrStatsW):
            upper, lower = self._model.tconfint_mean(alpha)
            return np.array([upper, lower])
        elif isinstance(self._model, RegressionResults):
            td = self.first_run - start_dt
            vals = {'timedelta': td.total_seconds()}
            df = pd.DataFrame(vals)
            prediction = self._model.get_prediction(df)
            return prediction.conf_int(alpha)[0, :]
        else:
            return np.array([0.0, self.initial_max_runtime])

@dataclass
class Routine:
    name: str
    run_time_confidence: float
    interval: int
    unit: str
    priority: int
    steps: List[Step]
    error_contacts: Tuple[str] = ()
    completion_contacts: Tuple[str] = ()

    def __str__(self):
        header = f'Routine: {self.name} runs every {self.interval} {self.unit}'
        steps = [f'Step {i}: {s}' for i,s in enumerate(self.steps)]
        body = '\n'.join(steps)
        return header+'\nSteps:\n'+body