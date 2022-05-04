# PiPyAWC
A dynamically-configurable & automated aquarium water level controller for the Raspberry Pi using Python. Intended to run using mechanical voltage relays (i.e. Waveshare Relay Hat) and optical contact liquid sensors (i.e. from DFRobot/CQRObot)

NOTE: This is a HIGHLY experimental program. I'm significantly behind on developing tractable unit tests w/ mock GPIO pins and it should go without saying that any electronics project involving water carries hazardous risks.


## Getting started

### Installation
1. Build package wheel from source
	
	```
	$ python3 ./setup.py bdist_wheel
	```

2. Install via pip

	```
	$ pip3 install ./dist/pipy-awc-0.5.0-py3-none-any.whl
	```

### Configuation

Fill out the config.yaml file as needed under ./data/

Environmental variables are supported in the .yaml file using the !EnvVar ${VAR_NAME} format. I recommend this in place of using plain-text. This is slightly more secure than working with raw text paswords and I recommend familiarizing yourself with [environmental variables and user permissions in Linux](https://security.stackexchange.com/questions/14000/environment-variable-accessibility-in-linux/14009#14009). Regardless, I recommend establishing a dedicated GMail account for this program and following Google's instructions for [less secure apps](https://support.google.com/accounts/answer/6010255?hl=en) which involves setting up revocable application password.

### Basic Usage

Start the program (assumes installed)

```
$ PiPy-AWC start --source ./path/to/your/config.yaml --interval REFRESH_RATE_SECONDS
```

Personally I attach this to a [tmux](https://man7.org/linux/man-pages/man1/tmux.1.html) session at boot.

There is also "remote CLI" for modifying behaviors mid-run (described below), I will not describe this here for now, as it's still quite buggy.


## Application design
Type-hints and useful docstrings are still a work in progress, as is this README. **Consider this a very early alpha distribution.**

Below I will attempt to highlight my main design patterns utilized.

### Controller
The key object is the Controller class contained in /src/modules/controller.py

This class has several child objects which it coordinates including the scheduler (and its jobs), the e-mail client (messenger), the routine templates used for jobs/dispenser logic, the dispenser (and its pumps), and the monitor (and its sensors). The Routine and Step dataclasses store information about how the dispenser should operate. 

### Peripherals
Dispenser and Monitor classes (contained in /src/modules/peripherals/) act as factories, which instantiate sensors/pumps and register them in dictionary attributes stored with the parent (dispenser/monitor) instance. Sensors report back to the monitor via an observer/callback pattern whenever their value changes).

Resolution of tank states by the monitor is done by a series of logical checks in which all sensors that *positively* report to a state must be True/1/GPIO.HIGH and all sensors that report *negatively* to a state must be False/0/GPIO.LOW. This is done by specifying state names as strings in on_submerged/on_exposed. Note that if more than one state is valid, TankErrorState will be returned. This should halt all programs from running. Your tank states should theoretically be set-up to ensure that multiple states can occur only if sensor has failed and is giving erroneous readings.

### Scheduler
The scheduler uses the schedule module, which also uses a factory pattern, where the scheduler instantiates jobs (i.e. job = schedule.every(interval)) and registers them with itself, runs them, and schedules the timing of further jobs using a convenient syntax inspired by natural language. I've extended both the schedule and job classes to implement some convenience features under /src/modules/operations/advanced_schedule.py

### Messenger
The messenger class (/src/modules/operations/messaging.py collects some functions from stmplib and imap-tools.

### CLI/Parsers
Contained in /src/ are several files for handling ArgumentParser activites.

Some of this is quite complicated as I've setup a series of subcommands that can be used mid-run as a sort of (remotely accessible CLI), either by texting the appropriate CLI string to the email associated with the messenger instance or by triggering a KeyboardInterrupt (i.e. ctrl+c 2x). For instance, a user can text the following command to perform the "Water Change" routine as a one-time routine at 10AM.

```
run "Water Change" --at 10:00:00
```

All such commands are technically setup as argparse subcommands under a parent parser. The start-up CLI parser, email "CLI" parser, and keyboard interrupt CLI parser are all separate instances. The functions/classes in ./pipyawc are all intended to put off the burden of instantiating these multiple, complex parsers to an area of the code outside of the main() function.

The file convenience_classes.py contains classes user for storing data related to different parser subcommands/arguments/argument groups and adding them to an existing parser. The parser_factory.py file implements functions which take in list-like tree structures of these objects and build up a parser from a base ArgumentParser class.

Pre-defined structures for each of the three parser types descrided above are hard-coded in arguments.py

The subcommands defined in this file have default functions which are defined in subcommand_funcs.py.
All of these functions take a dictionary of parsed arguments and a Controller instance and return a tuple containing the controller instance + some other values that vary by parser type.

Sometimes these subcommands require helper functions to process complex arguments and these are defined in argument_funcs.py

For instance, in the run "Water Change" --at 10:00:00" example above, run is defined in subcommand_funcs.py as a Python function and as a subnode (of the Subcommand class) of the REMOTE_CLI tree structure in arguments.py, the --at optional flag is defined further down within that same tree structure and as a function in argument_funcs.py and called by the run() func as needed.


## Statistical modeling of pump run times.
Right now I'm assuming that pump times are approximately normally distributed but may be affected by how long the pump has been in use. I'll make changes as needed if this assumption is incorrect. For now this is experimental.

Currently, max run times for each step of a routine is calculated based on a t-Distribution if runtime samples (n) are >= 10 n < 30.  If n >= 30 performs an OLS regression using time elapsed since the first run (in the future I will make a way to label/reset when pumps are replaced). If runtime samples are < 10, it will use the initial_max_runtime parameter which should be set using your best judgement based on expected pump output (i.e. via manufacturer) and fill volumes.

The confidence interval set in your configs for that routine will determine an upper/lower bound for the prediction based on how frequently you want to flag potential anomalies (1-confidence interval)/2.

In the future I may look into adding L1 regression along with information from the error check sensors as a model once samples are sufficiently large (i.e. >= 100) using RMSEP/cross-validation to estimate prediction intervals. My initial assumption is that w/o regularization, providing these as predictors would produce low-quality models. For instance, a sensor which is placed at a level that corresponds to a meaningful head pressure change for the pump may be useful to include, but this will vary between setups quite greatly. Thus L1 regularization is needed for feature selection.

In all cases, the model will only update/train/fit when first initializing the program and then again based on the time interval supplied in the config file to limit performance hits. In the long-term I'll look into implementing some binning/aggregation features (particularly important for evaporative loss replacement routines which might run with high frequency).


## Known Issues
* Several mid-run CLI options are buggy/behave unexpectedly and need to be fixed
* Some sensors are excessively sensitive and continually swing back and forth between submerged/exposed states when the water surface they are in contact with has high flow. A future version will address this with some signal smoothing.
	* As of 1/30/2022 this has been indirectly address by adding a bounce_time parameter to the dispenser class, for a 60 sq. inch return area, setting this to .1 (seconds) works well


## To-Dos
* Create a setup.sh to handle cron job scheduling that will ensure the program always starts on boot and re-starts if it crashes (will probably set-up some environmental variables tied to the Python script to make sure this is handled effectively)
	* will also handle setup for a shell manager (probably tmux since it is pre-installed on Raspbian) so that you can remote into the process from another machine to use keyboard interrupts if needed. Note that the availability of keyboard interrupts is a backup feature, my main intent is to provide mid-run CLI activity via email. Email commands will not disrupt normal activity, but keyboard interrupts may mess up ongoing runs.
* Break up more Controller class functionality, possibly:
	* Moving more responsibility for modeling to the Routine/Step classes (possibly move away from dataclass structure for these altogether)
	* Move more controller.run_routine() functionality to the dispenser.
* Thorough unit testing + emulator using the tkgpio library so users can simulate tank activity dynamically on non-RaspberryPi infrastucture
	* I haven't found time to properly read up on how gpiozero's mock pin factories work to establish these. Thus far my testing has been on physical hardware using buckets (and more recently my actual reef aquarium)


## Dependencies
* Python (probably ~=3.6+)
* numpy
* pandas
* scipy
* statsmodel
	* which itself requires scipy, numpy, pandas)
* pyaml
* schedule
* gpiozero (should be included w/ default Raspbian install)
* imap-tools


## Schematics/pics coming soon
Come back later!
