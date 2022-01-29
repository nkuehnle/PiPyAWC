# PiPyAWC
A dynamically-configurable & automated aquarium water level controller for the Raspberry Pi using Python. Intended to run using mechanical voltage relays (i.e. Waveshare Relay Hat) and optical contact liquid sensors (i.e. from DFRobot/CQRObot)

# Getting started
Fill out the config.yaml file found in the template folder as needed and place it in /data/config.yaml

Start the program with: python3 ./PiPyAWC/main.py start --interval \[refresh rate in integer seconds\]

# Application design
Docstrings/comments are still a work in progress, as is this readme. **Consider this a very early alpha distribution.**

The key object is the Controller class contained in /src/modules/controller.py

This class has several child objects which it coordinates including the scheduler (and its jobs), the e-mail client (messenger), the routine templates used for jobs/dispenser logic, the dispenser (and its pumps), and the monitor (and its sensors).

Sensor and monitor classes (contained in /src/modules/peripherals/) act as factories, which instantiate and register sensors/pumps. Sensors report back to the monitor via an observer pattern.

The scheduler uses the schedule module, which also uses a factory pattern, where the scheduler instantiates jobs (i.e. job = schedule.every(interval)) and registers them, runs them, and schedules repeating jobs. I've extended both classes for my convenience under /src/modules/operations/advanced_schedule.py

The messenger class (/src/modules/operations/messaging.py collects some functions from stmplib and imap-tools.

Contained in /src/ are several files for handling ArgumentParser activites. Some of this is quite complicated as I've setup a series of subcommands that can be used mid-run, either by texting the appropriate CLI string to the email associated with the messenger instance or by triggering a KeyboardInterrupt (i.e. ctrl+c 2x)

# Statistical modeling of pump run times.
Right now I'm assuming that pump times are normally distributed, but may be affected by how long the pump has been in use or water volume in the reservoirs (detectable if you are using the error_sensor option in the configs and have placed sensors in your reservoirs at a useful level). I'll make changes as needed if this assumption is incorrect.

Currently, max run times for each step of a routine is calculated based on a t-Distribution if samples are less than 10. Otherwise, it performs a multivariable regression using information about the various sensors (only if historical run data is available) and time elapsed since the first run (in the future I will make a way to label/reset when pumps are replaced). The confidence interval set in your configs for that routine will determine an upper bound for the prediction based on how frequently you want to flag potential anomalies. In the future I may look into adding an LTSM with confidence intervals once a large number of samples are available. The model will only update/train/fit when first initializing the program and then again based on the time interval supplied in the config file.

# Known Issues
* Several mid-run CLI options are buggy/behave unexpectedly and need to be fixed
* Some sensors are excessively sensitive and continually swing back and forth between submerged/exposed states when the water surface they are in contact with has high flow. A future version will address this with some signal smoothing.

# To-Dos
* Create setup.py/cleanup project structure
* Create a setup.sh to handle cron job scheduling that will ensure the program always starts on boot, will also handle setup for a shell manager so that you can remote into the process from another machine to use keyboard interrupts if needed. Note that the availability of keyboard interrupts is a backup feature, my main intent is to provide mid-run CLI activity via email. Email commands will not disrupt normal activity, but keyboard interrupts may mess up ongoing runs.
* Break up more Controller class functionality, possibly:
	* Moving more responsibility for modeling to the Routine/Step classes (possibly move away from dataclass structure for these altogether)
	* Move more controller.run_routine() functionality to the dispenser.
* Thorough unit testing + emulator using the tkgpio library so users can simulate tank activity dynamically on non-RaspberryPi infrastucture

# Dependencies
Will add requirements.txt soon.
* Python (probably 3.7 or 3.8+, need to confirm)
* pandas
* numpy
* statsmodel (which itself requires scipy, numpy, pandas)
* PyYAML
* schedule
* gpiozero (should be included w/ Raspbian)
* imap-tools

# Schematics/pics coming soon
Come back later!

