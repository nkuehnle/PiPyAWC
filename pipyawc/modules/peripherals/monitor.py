from abc import abstractmethod
from functools import wraps
from typing import Dict, List, Union

from gpiozero import DigitalInputDevice

from pipyawc.awclogger import logger

from .peripheral_errors import CheckError, ErrorSensorTriggered, SensorInstanceError


class Sensor(DigitalInputDevice):
    def __init__(self, monitor: "Monitor", name: str, pin: int, **kwargs):
        """A parent class for TankSensor and ErrorSensor to inherit from.

        Parameters
        ----------
        monitor : Monitor
            The parent monitor of this pump.
        name : str
            A descriptive name for the sensor
        pin : int
            The broadcom (BCM) pin number for the sensor
        """
        super().__init__(pin, **kwargs)
        self.monitor = monitor
        self.name = name
        self.monitor.sensors[self.name] = self.value
        self.when_activated = self.notify_monitor
        self.when_deactivated = self.notify_monitor

    @abstractmethod
    def notify_monitor(self):
        """
        An abstract method for notifying the monitor -- differs by subclass
        """
        raise NotImplementedError("Implement this function")


class TankSensor(Sensor):
    def __init__(
        self,
        monitor: "Monitor",
        name: str,
        pin: int,
        when_submerged: List[str],
        when_exposed: List[str],
    ):
        """A class to represent a standard tank sensor which defines the level
        in the main tank when deciding when to start/end routine steps.

        Parameters
        ----------
        monitor : Monitor
            The parent monitor of this pump.
        name : str
            A descriptive name for the sensor
        pin : int
            The broadcom (BCM) pin number for the sensor
        when_submerged : List[str]
            A list of tank states to report as True when submerged, otherwise reports
            False
        when_exposed : List[str]
            A list of tank states to report as True when exposed, otherwise reports
            False
        """
        super().__init__(monitor, name, pin)
        self.when_submerged = when_submerged
        self.when_exposed = when_exposed

    def _update_state_vals(self, set_true: List[str], set_false: List[str]):
        """
        [summary]

        Parameters
        ----------
        set_true : List[str]
            A list of tank states to report a True contribution to the monitor, if all
            other sensors report True to the monitor for this state, it will be eligible
            to be considered active.
        set_false : List[str]
            A list of tank states to report a False contribution to the monitor,
            this will always mean that those tank states are not considered active
        """
        for s in set_true:
            self.monitor.tank_states[s][self.name] = True
        for s in set_false:
            self.monitor.tank_states[s][self.name] = False

    @wraps(_update_state_vals)
    def notify_monitor(self) -> None:
        """
        Wraps _update_state_vals()
        """
        if self.value == 1:
            self._update_state_vals(self.when_submerged, self.when_exposed)
        elif self.value == 0:
            self._update_state_vals(self.when_exposed, self.when_submerged)


class ErrorSensor(Sensor):
    def __init__(
        self,
        monitor: "Monitor",
        name: str,
        pin: int,
        trigger_when: str,
        permitted_runs: int,
    ):
        """A class to represent an error sensor which has the potential to terminate
        routine steps early based on an alloted number of remaining runs. An example is
        a sensor which senses when an RODI reservoir is low.

        Parameters
        ----------
        monitor : Monitor
            The parent monitor of this pump.
        name : str
            A descriptive name for the sensor
        pin : int
            The broadcom (BCM) pin number for the sensor
        trigger_when : str
            Whether the sensor should report errors when 'submerged' or 'exposed'
        permitted_runs : int
            Maximum number of runs to allow once the sensor is triggered, this
            value is used to reset the remaining_runs attribute when the sensor
            is no longer in the triggered state.
        """
        super().__init__(monitor, name, pin)
        self.trigger_when = trigger_when
        self.permitted_runs = permitted_runs
        self.remaining_runs = self.permitted_runs

    def _update_status(self, state: str):
        """
        Compares the new status to the trigger state and informs the monitor
        whether the error is active and in the case of an non-triggered state,
        makes sure that remaining_runs has been reset to the maximum allowed.

        Parameters
        ----------
        state : str
            'submerged' or 'exposed'
        """
        if state == self.trigger_when:
            self.monitor.error_checks[self.name] = True
        else:
            self.remaining_runs = self.permitted_runs
            self.monitor.error_checks[self.name] = False

    @wraps(_update_status)
    def notify_monitor(self):
        """
        Wraps _update_status()
        """
        if self.value:
            self._update_status("submerged")
        else:
            self._update_status("exposed")


class Monitor:
    def __init__(
        self,
        sensors: Dict[str, Union[TankSensor, ErrorSensor]] = {},
        tank_states: Dict[str, Dict[str, bool]] = {},
        error_checks: Dict[str, bool] = {},
    ):
        """
        Objects instantiated by the :class: Monitor are factories which create
        sensors and implement an observer-pattern in which the sensors report
        their respective contribution(s) to a larger state

        Parameters
        ----------
        sensors : Dict[str, Union[TankSensor, ResevoirSensor]], optional
            A dictionary of sensor names (as strings) as keys and instances of objects
            inheriting from :class: Sensor, by default {}
        tank_states : Dict[str, List[bool]]], optional
            A dictionary of possible tank states (as strings) as high-level keys and a
            dictionary of lower-level keys given by all the sensors that affect that
            state. The values are interpreted indirectly, by :property: tank_state.
            By default, {}
        error_checks : Dict[str, bool], optional
            A dictionary of error check names (as strings) as keys and whether the
            associated sensor is actively triggered. The values are interpreted
            indirectly by :meth: check_error. By default, {}
        """
        self.sensors = sensors
        self.tank_states = tank_states
        self.error_checks = error_checks

    def register(
        self, sensor_type: str, name: str, pin: int, **kwargs
    ) -> Union[TankSensor, ErrorSensor]:
        """Instantiates a new object inheriting from :class: Sensor and stores it in the
        sensors attibute dictionary.

        Parameters
        ----------
        sensor_type : str
            The type of sensor to instantiate. Primarily used as a validation method to
            ensure that appropriate arguments are passed. Can be either 'error' or 'tank'
        name : str
            A descriptive name for the sensor
        pin : int
            The broadcom (BCM) pin number for the sensor
        kwargs
            All of the arguments which are specific to one sublass of Sensor or the
            other.

        Returns
        -------
        Union[TankSensor, ErrorSensor]
            [description]

        Raises
        -------
        SensorInstanceError
            Raised if sensor type and provided arguments mismatch.
        """
        try:
            if sensor_type == "tank":
                when_submerged: List[str] = kwargs["when_submerged"]
                when_exposed: List[str] = kwargs["when_exposed"]
                state_set = set(when_submerged + when_exposed)

                for state in state_set:
                    if state not in self.tank_states:
                        self.tank_states[state] = {}

                sensor = TankSensor(monitor=self, name=name, pin=pin, **kwargs)

            elif sensor_type == "error":
                sensor = ErrorSensor(monitor=self, name=name, pin=pin, **kwargs)

            self.sensors[name] = sensor
            sensor.notify_monitor()
            logger.debug(
                f"Registered {sensor_type} sensor {sensor.name} on pin {sensor.pin}"
            )
        except TypeError:
            kwargs = {"name": name, "pin": pin, **kwargs}
            raise SensorInstanceError(kwargs, sensor_type)

        return sensor

    @property
    def sensor_values(self) -> Dict[str, bool]:
        return {f"{sn} ({so.pin})": so.value for sn, so in self.sensors.items()}

    @property
    def tank_state(self) -> Union[str, CheckError]:
        """
        A property which returns the current state of the monitored tank.

        For a tank state to be found, all of the reporting tank sensors must
        report a TRUE value to the monitor for that state. Note that this is
        not always the same as the logic level of the sensor, as it depends on
        whether the sensor reports to the state when_submerged or when_exposed.

        Returns
        -------
        tank_state : str | CheckError
            A string representing the tank state. If a CheckError is returned, then no
            valid tank state was found. In most cases this indicates either improper
            configuration or a malfunctioning sensor. If this is reported during a
            routine, the program (via the Controller/Messenger) will generally notify
            all error contacts for that routine.
        """
        state_reports = {}
        for state, records in self.tank_states.items():
            state_reports[state] = all(records.values())

        if sum(state_reports.values()) == 1:
            states = [k for k, v in state_reports.items() if v]
            return states[0]
        else:
            return CheckError()

    def check_error(
        self, name: str, decrement: bool = True
    ) -> Union[bool, ErrorSensorTriggered]:
        """A function to check a specific, named error sensor.
        This method is typically used to report on and track reservoir levels.

        Parameters
        ----------
        name : str
            A descriptive name for the sensor
        decrement : bool, optional
            Whether to decrease the remaining_runs (only relevant if triggered),
            by default True

        Returns
        -------
        bool | ErrorSensorTriggered
            Either False (no error) or the details of the error triggered (which
            evaluates as True)
        """
        state = self.error_checks[name]

        if state and decrement:
            self.sensors[name].remaining_runs -= 1

        remaining_runs = self.sensors[name].remaining_runs

        if state:
            return ErrorSensorTriggered(name, remaining_runs)
        else:
            return False

    def any_errors(self) -> bool:
        """_summary_

        Returns
        -------
        bool
            _description_
        """
        in_error = [e for e in self.error_checks.values()]
        in_error.append(isinstance(self.tank_state, CheckError))
        return any(in_error)
