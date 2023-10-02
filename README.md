# PiPyAWC
A dynamically-configurable & automated aquarium water level controller for the Raspberry Pi using Python. Intended to run using mechanical voltage relays (i.e. [Waveshare Relay Hat](https://www.waveshare.com/rpi-relay-board.htm) or [Pimoroni's automation hat](https://shop.pimoroni.com/products/automation-hat?variant=30712316554)) and optical contact liquid sensors (i.e. from DFRobot/[CQRObot optical level sensors](https://www.cqrobot.com/index.php?route=product/product&product_id=1101))

NOTE: This is an experimental program for personal use. I'm significantly behind on developing tractable unit tests w/ mock GPIO pins and **it should go without saying that any electronics project involving water carries hazardous risks, use electronics rated for submersible applications, such as the sensors listed above**. Currently unit tests are only implemented for basic core CLI/paser functions, function of the main modules


## Getting started

### Installation
1. Build package wheel from source
	
	```
	$ python3 ./setup.py bdist_wheel
	```

2. Install via pip

	```
	$ pip3 install ./dist/pipy-awc-0.8.0-py3-none-any.whl
	```

### Configuation

Fill out the config.yaml file as desired. There is an example under ./data/config.yaml -- some features are described in greater detail with config examples below.

Note: Environmental variables are supported in the .yaml file using the !EnvVar ${VAR_NAME} syntax. I recommend this in place of using plain-text for sensitive records. This is slightly more secure than working with raw text paswords and I recommend familiarizing yourself with [environmental variables and user permissions in Linux](https://security.stackexchange.com/questions/14000/environment-variable-accessibility-in-linux/14009#14009). Regardless, I recommend establishing a dedicated GMail account for this program and following Google's instructions for [less secure apps](https://support.google.com/accounts/answer/6010255?hl=en) which involves setting up revocable application password. I have run my controller off of a single, dedicated GMail account since late 2021.

### Basic Usage

Start the program (assumes installed)

```
$ PiPy-AWC start --source ./path/to/your/config.yaml --interval REFRESH_RATE_SECONDS
```

Personally, I attach this to a [tmux](https://man7.org/linux/man-pages/man1/tmux.1.html) session at boot.

```
# Create session
$ tmux new-session -d -s pipyawc
# Send start command to tmux session as keys
$ tmux send-keys -t pipyawc C-z "PiPy-AWC start --source ./config.yaml --interval 1 " Enter
```

There is also "remote CLI" for modifying behaviors mid-run (described below), I will not describe this here for now, as it's still quite buggy.

To connect to a tmux session to monitor/modify behavior via ssh/directly on device, use:
```
$ tmux attach-session -t pipyawc
```

See the examples in ./data/config.yaml for examples on how to properly configure pumps, sensors, and basic tank settings.


## Application design
Typehints and docstrings are fairly extensive throughout the codebase. **Consider this a very early alpha distribution of this program since test coverage is mimimal/limited to command line and basic controller functions.**

Below I will attempt to highlight the main elements of the program below.

### Project stucture
The `pipyawc/modules` folder contains core functions required to run the raspberry pi and its physical activities. It has two sub-modules, operations (scheduling, messenger code, etc) and peripherals (abstractions and code for sensors, pumps and routines). In the main source `pipyawc/` directory are several modules which abstract the two types of CLIs.
```
├── bin
│   └── PiPy-AWC
├── data
│   └── config.yaml
├── pipyawc
│   ├── arg_funcs.py
│   ├── arguments.py
│   ├── convenience_classes.py
│   ├── __init__.py
│   ├── modules
│   │   ├── controller.py
│   │   ├── __init__.py
│   │   ├── operations
│   │   │   ├── advanced_schedule.py
│   │   │   ├── environmental_vars.py
│   │   │   ├── __init__.py
│   │   │   ├── messaging
│   │   │   │   ├── email_messenger.py
│   │   │   │   ├── __init__.py
│   │   │   │   └── _messenger.py
│   │   │   └── messaging.py
│   │   └── peripherals
│   │       ├── dispenser.py
│   │       ├── __init__.py
│   │       ├── monitor.py
│   │       ├── peripheral_errors.py
│   │       └── routines.py
│   ├── parser_factory.py
│   ├── parsing.py
│   └── subcommand_funcs.py
├── pyproject.toml
├── README.md
├── requirements.txt
├── setup.py
└── tests
    ├── commands.json
    ├── _parser_helpers.py
    └── test_parser.py
```
### Controller
The key object is the Controller class contained in `pipyawc/modules/controller.py`

This class has several child objects which it coordinates including the scheduler (and its jobs), the e-mail client (messenger), the routine templates used for jobs/dispenser logic, the dispenser (and its pumps), and the monitor (and its sensors). The Routine and Step dataclasses store information about how the Dispenser should operate. The Controller is the glue that holds all of these together.

### Peripherals
Dispenser and Monitor classes (contained in `pipyawc/modules/peripherals/`) act as factories, which instantiate sensors/pumps and register them in dictionary attributes stored with the parent (dispenser/monitor) instance.


Sensors report back to the Monitor class via an observer/callback pattern whenever their value changes) and live in `pipyawc/modules/peripherals/monitor.py`.

Resolution of tank states by the monitor is done by a series of logical checks in which all sensors that *positively* report to a state must be True/1/GPIO.HIGH and all sensors that report *negatively* to a state must be False/0/GPIO.LOW. This is done by specifying state names as strings in on_submerged/on_exposed. Note that if more than one state is valid, TankErrorState will be returned. This should halt all programs from running. Your tank states should theoretically be set-up to ensure that multiple states can occur only if sensor has failed and is giving erroneous readings.

An example of a tank state in a two monitor system would be a normal level sensor and a low level sensor. Both sensors would report to a full tank state when submberged and to a low tank level when exposed. When the normal level sensor is exposed and the low level sensor is submerged, it would be a "draining" state. See the below config example with two example sensors. Tank states are the primary means by which the steps of a routine proceed in order to modify the water level in the tank.

```
tank_sensors:
  - pin: 26
    name: Normal Level
    when_submerged: [full]
    when_exposed: [low, draining]
  - pin: 20
    name: Low Level
    when_submerged: [full, draining]
    when_exposed: [low]
```

Error checks are sensors which trigger a particular error state either when exposed or when submerged. These can add additional safety/quality checks on steps. For instance, you may include an error check to abort a water change if there is no saltwater available to replace water that is drained from the tank during a water change routine before the tank is drained.

```
error_sensors:
  - pin: 21
    name: Saltwater
    trigger_when: exposed
    permitted_runs: 1
  - pin: 5
    name: RODI
    trigger_when: exposed
    permitted_runs: 10
  - pin: 17
    name: Wastewater
    trigger_when: submerged
    permitted_runs: 1
```

Pumps are more simple and simply have names and pin configurations. They have a parent in the form of the Dispenser class and live in `pipyawc/modules/peripherals/dispenser.py`

```
pumps:
  - name: Wastewater Pump
    pin: 13
    active_high: True
  - name: Saltwater Pump
    pin: 16
    active_high: True
  - name: RODI Pump
    pin: 19
    active_high: True
```

### Routines and Steps
Routines are a series of steps which have finite tank states that start and end them (and optional errors which can impact their behavior further).  Both Routines and Steps are implemented as dataclases in `pipyawc/modules/peripherals/routines.py` and they represent the core steps that the Dispenser needs to act upon.

An example of two basic functions, a water change and topping off the tank (i.e. replacing evaporated water) are described below (these assume low flow capacity peristaltic pumps). A routine can optionally continue to proceed if the step prior timed out or returned an error. These will still be reported to any error contacts. This can be desired behavior for certain steps, like running a top-off of RODI water prior to draining the tank, since this step may not always need to run. A critical failure is an error or timeout in which the routine is set to *not proceed*. In these cases, the routine can be canceled or not (continued to re-schedule) based on desired behavior.
```
routines:
  - name: Water-Change
    interval: 21
    unit: hours
    priority: 1
    error_contacts: [USER_EMAIL, USER_PHONE]
    completion_contacts: [USER_EMAIL, USER_PHONE]
    steps:
      - name: Top Off
        start_states: [draining]
        end_states: [full]
        pump: RODI Pump
        error_checks: [Saltwater]
        proceed_on_invalid_start: True
        proceed_on_timeout: False
        proceed_on_error: False
        cancel_on_critical_failure: False
        max_runtime: 15
      - name: Drain Tank
        start_states: [full]
        end_states: [low]
        pump: Wastewater Pump
        error_checks: [Saltwater]
        proceed_on_invalid_start: False
        proceed_on_timeout: True
        proceed_on_error: True
        cancel_on_critical_failure: False
        max_runtime: 500
      - name: Refill Tank
        start_states: [low, draining]
        end_states: [full]
        pump: Saltwater Pump
        error_checks: [Saltwater, Wastewater]
        proceed_on_invalid_start: True
        proceed_on_timeout: True
        max_runtime: 500
  - name: Top-Off
    interval: 1
    unit: minutes
    priority: 2
    error_contacts: [USER_EMAIL, USER_PHONE]
    completion_contacts: []
    steps:
      - name: Refill
        start_states: [draining, low]
        end_states: [full]
        pump: RODI Pump
        error_checks: [RODI]
        report_invalid_start: False
        proceed_on_invalid_start: True
        proceed_on_timeout: True
        max_runtime: 300
```

### Scheduler
The scheduler uses the schedule module, which also uses a factory pattern, where the scheduler instantiates jobs (i.e. job = schedule.every(interval)) and registers them with itself, runs them, and schedules the timing of further jobs using a convenient syntax inspired by natural language. I've extended both the schedule and job classes to implement some convenience features under /src/modules/operations/advanced_schedule.py

### Messenger
The EmailMessenger class (`pipyawc/modules/operations/messaging.py` collects some functions from stmplib and imap-tools. There is an abstract imlementation in the form of Messenger class, but currently there are not other modes of messaging between the program and user besides smtp/imap emails.

### CLI/Parsers
Contained in /src/ are several files for handling ArgumentParser activites.

* `convencience_classes` provides abstract representations of types of argpase CLI functionalities
	* subcommands, arguments, argument groups, etc.
	* a function for building the parser using these that chains downward to build out a CLI from a tree-like structure is provided in the form of the add_to() function
* `arguments` defines fixed/constant objects (from `convencience_classes`) using the abstract representations, it includes the specific functionalities that different arguments or subcommands may serve to fill from `arg_funcs` and `subcommand_funcs`
	* In the end each component winds up as a leaf/node of the REMOTE_CLI or STANDARD_CLI objects defined at the end of the file
* `arg_funcs` define functions useful for processing the input of arguments to different subcommand (i.e. "--at 10:00:00")
* `subcommand_funcs` defines functions used when a subcommand is run (i.e. "run [routine] --at [time]"
	* the standard CLI has one sucommand "start" returns the controller and the interval to update it at.
	* the remote CLI has multiple subcommands all of which expect a controller instance and returns a pair of values related to whether the action succeeded or failed
* `parser_factor` is contains functions for instantiating the structures (REMOTE_CLI, and STANDARD_CLI) defined in `arguments` as actual argparse parser objects
* `parsing` contains functions for parsing standard or remote CLI arguments.
	* Standard CLI takes the namespace of the parser
	* Remote CLI also needs the active controller instance and information about who to contact/how to relay information about whether the job succeeded or not (i.e. print to terminal if input at terminal, email original sender if the command was received via email)


Some of this functionality is quite complicated as I've setup a series of subcommands that can be used mid-run as a sort of remotely accessible CLI. This "remote/interrupt CLI" can be accessed either by texting/emailing the appropriate CLI string to the email associated with the messenger instance or by triggering a KeyboardInterrupt (i.e. ctrl+c 2x). For instance, a user can text the following command to perform the "Water Change" routine as a one-time routine at 10AM.

```
run "Water Change" --at 10:00:00
```

or in 5 minutes

```
run "Water Change" --in "5" "minutes"
```

All such commands are technically setup as argparse subcommands under a parent parser. The start-up CLI parser, email "CLI" parser, and keyboard interrupt CLI parser are all separate instances. The functions/classes in ./pipyawc are all intended to put off the burden of instantiating these multiple, complex parsers to an area of the code outside of the main() function.

The file convenience_classes.py contains classes user for storing data related to different parser subcommands/arguments/argument groups and adding them to an existing parser. The parser_factory.py file implements functions which take in list-like tree structures of these objects and build up a parser from a base ArgumentParser class.

Pre-defined structures for each of the three parser types descrided above are hard-coded in arguments.py

The subcommands defined in this file have default functions which are defined in subcommand_funcs.py.
All of these functions take a dictionary of parsed arguments and a Controller instance and return a tuple containing the controller instance + some other values that vary by parser type.

Sometimes these subcommands require helper functions to process complex arguments and these are defined in argument_funcs.py

For instance, in the run "Water Change" --at 10:00:00" example above, run is defined in subcommand_funcs.py as a Python function and as a subnode (of the Subcommand class) of the REMOTE_CLI tree structure in arguments.py, the --at optional flag is defined further down within that same tree structure and as a function in argument_funcs.py and called by the run() func as needed.

## Known Issues
* Several mid-run/KeyBoardInterrupt CLI options are buggy/behave unexpectedly and need to be fixed (i.e. pausing a job)
* Some sensors are excessively sensitive and continually swing back and forth between submerged/exposed states when the water surface they are in contact with has high flow. A future version will address this with some signal smoothing.
	* As of 1/30/2022 this has been indirectly address by adding a bounce_time parameter to the dispenser class, for a 60 sq. inch return area, setting this to .1-2 seconds works well in my time (will depend on the speed of the pumps utilized)

## To-Dos
* Create a setup script to handle cron job scheduling that will ensure the program always starts on boot and re-starts if it crashes (will probably set-up some environmental variables tied to the Python script to make sure this is handled effectively)
	* will also handle setup for a shell manager (probably tmux since it is pre-installed on Raspbian) so that you can remote into the process from another machine to use keyboard interrupts if needed. Note that the availability of keyboard interrupts is a backup feature, my main intent is to provide mid-run CLI activity via email. Email commands will not disrupt normal activity, but keyboard interrupts may mess up ongoing runs.
* Break up more Controller class functionality, possibly:
	* Moving more responsibility for modeling to the Routine/Step classes (possibly move away from dataclass structure for these altogether)
	* Move more controller.run_routine() functionality to the dispenser.
* Thorough unit testing + emulator using the tkgpio library so users can simulate tank activity dynamically on non-RaspberryPi infrastucture
	* I haven't found time to properly read up on how gpiozero's mock pin factories work to establish these. Thus far my testing has been on physical hardware using buckets (and more recently my actual reef aquarium)


## Dependencies
* python>=3.7
	* probably runs fine on 3.6+
* pandas>=1.3
* pyaml>=21.10
* schedule>=1.1.0
* gpiozero>=1.6.2
* imap-tools==0.55.0

## Schematics/pics coming soon
Come back later!
