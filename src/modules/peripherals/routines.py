from dataclasses import dataclass, field
from typing import Tuple, List, Union
from pathlib import Path
import datetime as dt
import sys
# Third-party module imports
import pandas as pd
import numpy as np
from statsmodels.regression.linear_model import RegressionResults
from statsmodels.stats.weightstats import DescrStatsW
#
from .monitor import Monitor

HOME_DIR = Path(__file__).parents[3]
LOG_DIR = HOME_DIR / 'data' / 'logs'
try:
    LOG_DIR.mkdir(parents=True, exist_ok=False)
except FileExistsError:
    pass

@dataclass
class Step:
    parent: 'Routine'
    name: str
    pump: str
    start_state: str
    end_state: str
    error_checks: Tuple[str]
    first_run: dt.datetime = None
    model_vars: List[str] = field(default_factory=list)
    report_invalid_start: bool = True
    proceed_on_invalid_start: bool = False
    proceed_on_timeout: bool = False
    proceed_on_error: bool = False
    cancel_on_critical_failure: bool = True
    model: Union[RegressionResults, DescrStatsW] = None

    def __str__(self):
        return f'{self.name} (max time = {self.max_time})'

    def max_time(self, start_dt: dt.datetime, monitor: Monitor) -> float:
        if self.model == None:
            return sys.float_info.max
        else:
            td = self.first_run - start_dt
            td = td.total_seconds()
            err_sensor_vals = {'timeout': False, 'timedelta': td}

            for var in self.model_vars:
                sensor = monitor.sensors[var.replace('_error', '')]
                err_sensor_vals[var] = sensor.remaining_runs

            return self.model.predict()
    
    def interval_range(self, start_dt: dt.datetime, monitor:
                       Monitor) -> np.ndarray:
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
        
        if isinstance(self.model, DescrStatsW):
            upper, lower = self.model.tconfint_mean(alpha)
            return np.array([upper, lower])

        elif isinstance(self.model, RegressionResults):
            td = self.first_run - start_dt
            vals = {'timedelta': td.total_seconds()}
            for var in self.model_vars:
                sensor = monitor.sensors[var.replace('_error', '')]
                vals[var] = sensor.remaining_runs

            df = pd.DataFrame(vals)

            prediction = self.model.get_prediction(df)
            return prediction.conf_int(alpha)[0, :]
            
        else:
            return np.array([0, sys.float_info.max])

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