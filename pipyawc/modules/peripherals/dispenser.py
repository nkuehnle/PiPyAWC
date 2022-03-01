# Default module imports
from typing import Dict, List, Tuple, Union
from functools import wraps
import time
# Third-party module imports
try:
    from gpiozero import DigitalOutputDevice
except ModuleNotFoundError as e:
    print(f"WARNING: please run pip install gpiozero")
    raise e
# Custom module imports
from .peripheral_errors import \
    PumpInstanceError, InitialStateError, PumpTimeoutError, ErrorSensorTriggered
from .monitor import Monitor
from .routines import Step

class Pump(DigitalOutputDevice):
    def __init__(self, dispenser: 'Dispenser', name: str, pin: int,
                 active_high: bool = True):
        """A pump object. The Dispenser class acts as a factory and indirect
        control interface for this object.

        Parameters
        ----------
        dispenser : Dispenser
            The parent dispenser of this pump.
        name : str
            A descriptive name for the pump.
        pin : int
            The broadcom (BCM) pin number for the relay
        active_high : bool, optional
            Whether logic level HIGH/1 is associated with an active relay, by
            default True
        """
        super().__init__(pin=pin, active_high=active_high, initial_value=False,
                         pin_factory=None)
        self.dispenser = dispenser
        self.name = name
        self.dispenser.pumps[self.name] = self

class Dispenser:
    def __init__(self, bounce_time: float = 0.0, pumps: Dict[str, Pump] = {}):
        """A factory class and a control interface for processing instances of
        the Step class.

        Parameters
        ----------
        bounce_time : float, optional
            A length of time (in seconds) to wait between subsequent monitor
            checks when running a routine step. Useful if sensor
            response time/sensitivity is too precise.
        pumps : Dict[str, Pump], optional
            A dictionary of pump names (as strings) as keys and instances of
            :class: Pump objects, by default {}
        """
        self.bounce_time = bounce_time
        self.pumps = pumps

    def register(self, name: str, pin: int, active_high: bool = True) -> Pump:
        """Instantiates a new :class: Pump object and stores it in the
        pumps attibute dictionary.

        Parameters
        ----------
        name : str
            A descriptive name for the pump.
        pin : int
            The broadcom (BCM) pin number for the relay
        active_high : bool, optional
            Whether logic level HIGH/1 is associated with an active relay, by
            default True

        Returns
        -------
        Pump
            The newly instantiated :class: Pump object

        Raises
        ------
        PumpInstanceError
            Raised if invalid arguments a provided for a new :class: Pump
            instance.
        """
        try:
            return Pump(self, name, pin, active_high=active_high)
        except TypeError:
            raise PumpInstanceError({'name': name, 'pin': pin})


    def _run_step(self, step: Step, monitor: 
                  Monitor) -> Union[float, Tuple[float, List[Exception]]]:
        """Runs the provided :class: Step instance, looping until the provided
        :class: Monitor instance returns a completion or error state; otherwise
        runs until the maximum time limit has been exceeded for that step.

        Parameters
        ----------
        step : Step
            An instance of :class: Step to process. Assumes that a valid start
            state was already processed.
        monitor : Monitor
            The active monitor provided to the Dispenser via their shared
            parent (an instance of :class: Controller)

        Returns
        -------
        Union[float, Tuple[float, List[Exception]]]
            Either the time for the run to complete or the time for the run and
            a list of errors returned. 
        """
        start_time = time.time()
        self.pumps[step.pump].on() # Turn pump on...
        run_time = time.time()-start_time
        max_time = step.max_time
        errs = [False for _ in step.error_checks]

        # While loop runs until end condition is met or an error state is found
        while monitor.tank_state != step.end_state:
            time.sleep(self.bounce_time)

            for i,check in enumerate(step.error_checks):
                errs[i] = monitor.check_error(check, decrement=not(errs[i]))

            if any(errs):
                for e in errs:
                    if isinstance(e, ErrorSensorTriggered):
                        if e.remaining_runs <= 0:
                            break

            run_time = time.time()-start_time
            if run_time >= max_time: # PumpTimeoutError if time ran out
                errs.append(PumpTimeoutError(step.pump, run_time))
                break

        self.pumps[step.pump].off() # Shut pump off.

        if any(errs):
            return (run_time, [e for e in errs if e])
        else:        
            return run_time
    
    @wraps(_run_step)
    def run_step(self, step: Step, monitor:
                 Monitor) -> Union[float, Tuple[float, List[Exception]]]:
        """
        A wrapper for _run_step() that checks and reports on the start status
        """
        if monitor.tank_state == step.start_state:
            ret = self._run_step(step, monitor)
        else:
            ret = InitialStateError(step.name, monitor.tank_state)     
        return ret