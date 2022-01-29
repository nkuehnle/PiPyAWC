# Default module imports
from typing import Dict
from abc import abstractproperty

class PeripheralInstanceError(Exception):
	def __init__(self, kwargs: Dict[str, object]):
		self.kwargs = kwargs
		self._classname = None
		
	@abstractproperty
	def expected_kwargs(self) -> Dict[str, str]:
		raise NotImplementedError('Implement this propery!')

	@property
	def missing_kwargs(self) -> Dict[str, str]:
		missing_kwargs = {}
		for k,v in self.expected_kwargs.items():
			if k not in self.kwargs.keys():
				missing_kwargs[k] = v
		return missing_kwargs

	@property
	def invalid_kwargs(self) -> Dict[str, str]:
		inv_kwargs = {}
		for k,v in self.kwargs.items():
			if k not in self.expected_kwargs.keys():
				inv_kwargs[k] = v.__class__.__name__
		return inv_kwargs

	def __repr__(self) -> str:
		passed_args =  [f'{k} = {v}' for k,v in self.kwargs.items()]
		expected_args = [f'{k}: {v}' for k,v in self.expected_kwargs.items()]

		clsname = self._classname
		
		passed = f"Passed: {clsname}({', '.join(passed_args)})"
		expected = f"Expected: {clsname}({', '.join(expected_args)})"

		return f"SensorInstanceError!\n{passed}\n{expected})"

class PumpInstanceError(PeripheralInstanceError):
	def __init__(self, kwargs: dict):
		self.kwargs = kwargs
		self._classname = 'Pump'
	
	@property
	def expected_kwargs(self) -> Dict[str, str]:
		return {'name': 'str', 'pin': 'int'}

class SensorInstanceError(PeripheralInstanceError):
	def __init__(self, kwargs: dict, sensor_type: str):
		self.kwargs = kwargs
		if sensor_type == 'tank':
			self._classname = 'TankSensor'
		elif sensor_type == 'reservoir':
			self._classname = 'Reservoir'
		else:
			self._classname = 'INVALID_SENSOR_NAME!!!'
	
	@property
	def expected_kwargs(self) -> Dict[str, str]:
		if self._classname == 'TankSensor':
			kwargs = {'when_submerged': 'List[str]', 
					  'when_exposed': 'List[str]'}
		elif self._classname == 'ReservoirSensor':
			kwargs = {'trigger_when': 'str',
					  'permitted_runs': 'int'}
		return kwargs

class PumpTimeoutError(Exception):
    def __init__(self, name, run_time):
        self.name = name
        self.run_time = run_time
    
    def __str__(self):
        lbl = f'{self.name} timed out.'
        return lbl + f' Maximum allowed duration is {self.run_time} seconds.'

class InitialStateError(Exception):
	def __init__(self, step, state):
		self.step = step
		self.state = state
	
	def __str__(self):
		return f'An incorrect initialization state ({self.state}) occured at step {self.step}'

class CheckError(Exception):
	def __init__(self, run_time: float = 0.0):
		self.run_time = run_time

	def __str__(self):
	  return 'No valid tank state was found'
  

class ErrorSensorTriggered(Exception):
	def __init__(self, name: str, remaining_runs: int, run_time: float = 0.0):
		self.name = name
		self.remaining_runs = remaining_runs
		self.run_time = run_time 

	def __str__(self):
		err_str = f"Sensor {self.name} detected a problem. "
		err_str += f"There are {self.remaining_runs} permitted runs remaining."
		return err_str