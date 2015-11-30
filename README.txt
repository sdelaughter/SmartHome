Author: Samuel DeLaughter
Last Updated: 4/10/15


ABOUT:
------

This is a distributed system simulating a home "internet-of-things" network composed of a gateway, backend database, and user terminal, along with several sensors and smart devices.

I initially created it as a project for my graduate course on Distributed Operating Systems at the University of Massachusetts Amherst.


EXECUTION:
----------

Each device is started by running its corresponding python file -- no options or arguments are necessary (or supported), and since they're all written in python no compilation or make files are necessary.  For convenience, a bash script (/iot/resources/start) is also included.  This script accepts a device name as an argument and executes it in python.  For example:

	To start the gateway, simply cd to the resources folder and enter:
		start gateway
	
	This is equivalent to entering:
		python gateway.py
	
The included device files are:
	gateway.py
		The gateway -- coordinates operations between all other devices
		
	backend.py
		The backend tier -- Manages the persistent databases
		
	bulb.py
		A smart light bulb -- can be turned on or off remotely, or queried for its current state
		
	outlet.py
		A smart outlet -- can be turned on or off remotely, or queried for its current state
		
	temp.py
		A temperature sensor -- turns on and off outlets (via the gateway) when temperature is below or above certain values
		
	motion.py
		A motion sensor -- turns on bulbs (via the gateway) when motion is detected
		
	door.py
		A door sensor -- pushes OPEN or CLOSED values to the gateway whenever its state changes, can also be queried
		
	presence.py
		A beacon on the user's keychain -- pushes its state to the gateway whenever it changes
		
	user_terminal.py
		A user terminal -- handles input to manually change the motion detection mode between HOME and AWAY
		
	user_display.py
		A user display -- shows alert messages and changes to the motion detection mode
		
		
All device files rely on iot.py for the generic device class definition, as well as some helper functions.  While only this file, the start script, and gateway_ip.txt (explained later) are required to be present for a device's python script to run, it's best practice to place a copy of the entire resources file on each machine that will be used.  Note that this is a trivial requirement when running the system on the edLab machines, since all files will be automatically replicated between all machines.

Devices can be started in any order, though it's most efficient to start the gateway first.  If another device is started first, it will repeatedly attempt to register with the gateway (and fail) every ten seconds, generating unnecessary overhead.  It's also wise to start the backend device early in the sequence (perhaps even before the gateway), or else some system events will be missing from the database files.

Any device can be stopped (with the standard Ctl-C keyboard interrupt command) and restarted with no adverse effects -- it will be reregistered at the gateway with a new ID number.  Certain functions on the gateway will check for dead devices in the registration list and delete them when found.  Their port numbers will be recycled, but never their IDs.

Devices which do not actively push to the gateway have no mechanism to check whether it's still up.  Thus, if the gateway goes down it's best to stop and restart all other devices -- otherwise some will become unresponsive, and some may continue listening on ports that the new gateway has assigned to different devices.  Future versions of this program could make use of the database files to re-establish past registrations upon a gateway's recovery in order to avoid having to undergo this tedious process.


CONFIGURATION:
-------------

When each non-gateway device starts up, it must check the gateway_ip.txt file in order to contact the gateway for registration. When the gateway starts, it writes its address to this file automatically.  Therefore, if the programs can all share the same gateway_ip.txt file, no manual configuration is necessary.  This feature works particularly well on EdLab, since even if the devices are running on separate machines, the gateway_ip.txt file will be replicated to all of them as soon as the gateway process writes to it.

If this replication does not or cannot occur, or if the file is deleted after the gateway writes to it, the gateway_ip.txt file must be written manually before any devices will be able to register with the gateway.  It must contain only the gateway's network address, formatted as follows on a single line:

http://ip:port

For example:
http://127.0.0.1:9000

Without replication, it's safest to start the gateway first and then manually copy the gateway_ip.txt file to the other machines -- this will ensure that the address is both accurate and properly formatted.

The included gateway_ip.txt file currently contains the address of elnux1.cs.umass.edu, where the gateway program was last run.  By default the gateway is set up to use port 9000, though this number can be set with the self.port attribute in the __init__ function for the gateway() class in gateway.py.


DESIGN:
-------
All device files are written in pure python (tested on version 2.7.3), and require no external libraries.  Python's xmlrpclib and SimpleXMLRPCServer modules are used for inter-device communication.  The execution file is a simple bash script.

The python scripts are highly object-oriented; each different device type has its own class, a new instance of which is created at the start of the main() function.

Device files can be distributed across as many or as few different physical machines as desired, as long as those machines are all IP-routable.  Each device on the same IP address gets a unique port number, starting at 9001 (the gateway always uses port 9000 no matter what other devices may be using its IP).

Any number of devices of the same type (with the exception of the gateway and backend) can be run simultaneously.  However, the gateway does not have the intelligence to -- for example -- assign a specific temperature sensor to a specific outlet.  Rather, devices with the same name are effectively grouped.  All outlets are turned on or off together, as are bulbs.  Temperature values are collected from all registered temperature sensors and averaged.  If any one presence sensor's state changes, the motion detection mode will change accordingly.  Whenever motion is detected by any motion sensor, the gateway will take appropriate action based on the current motion mode.  Only one instance of the gateway should ever be running at any given time, and the system has never been tested with multiple backend devices.

Since no actual sensor hardware is available for this project, sensor processes implement naive sense() functions whenever their states are queried.  Temperature sensors randomly return an integer between -20 and 40.  Motion sensors have a 1/4 chance of changing their state each time their sense() function is run, and report to the gateway whenever their state is 1.  Presence sensors also have a 1/4 chance of changing their state each time their sense() function is run, but only report to the gateway when their state actually changes.

The user process is split into two separate devices, a terminal and a display.  If they were combined, displaying an alert message would require getting a lock to interrupt the user input thread.  When the user enters a command into the terminal device, the results will be printed to the display device.  However, if the user enters an invalid command, a list of valid commands will be displayed directly at the terminal before initiating the next input prompt.

All device processes are multi-threaded, but no locks are implemented.  Rather, the sending of messages is designed in a way that should naturally avoid any potential deadlock scenarios.  If device A triggers a remote script on device B, that script will never attempt to contact A before returning a response to the original request.


LOGGING:
--------

Each program records detailed logs in the resources/logs folder, which will be created by the program if it doesn't already exist.  Log files are named with the device name and the timestamp at the time of the file's creation.  Therefore, anytime a program is stopped and restarted it will generate a new log file instead of overwriting the old one.

Each entry in a log file is formatted as follows:
	Logging_Level | Function_Name | Logical_Clock_Value | Timestamp: Message
	
For example:
	DEBUG | update_clock | 34 | 1428633420.24: Updated clock value to 34


DATABASE STRUCTURE:
------------------

Persistent databases are managed by python's shelve object.  The backend creates files name with a timestamp so that separate sessions can be distinguished and databases don't have to be erased between runs.  These files are not human readable, but manually accessing their information can be easily done with just a few lines of code in python's interactive mode.  For example:

	To print the value stored at key 'foo' in the state database file created at 5:00:00PM on April 10th, 2015 simply enter:
		cd iot/resources
		python
		>>> import shelve
		>>> file = shelve.open('db/2015_4-10_17-00-00_state.db')
		>>> value = file['foo']
		>>> print value
		
More information on the shelve module can be found at https://docs.python.org/2/library/shelve.html

The database structure itself differs between the state and history files.  In the state file, a descriptive string is used as the key (for example: 'outlet'), and the value is a 3-tuple of (value, logical_clock_value, timestamp).  In the history file, the key is the backend device's logical clock value, and the value is a 3-tuple of (k, value, timestamp), where k is the same descriptive string used as the actual key in the state file.  This structure allows devices to simultaneously write to both files with a single db_put(clock, key, value) command.  Since the backend device's logical clock is updated before every write, history items will never be overwritten while state items will.


LEADER ELECTIONS:
-----------------

Since the gateway's livelihood is mandatory for proper system functioning, leader elections are carried out via a modified version of the bully algorithm that's tailored to set the gateway as the leader whenever possible.  Once a device registers with the gateway, it initiates an election.  First, it contacts the gateway to retrieve an up-to-date list of all registered devices.  Next, it goes through each item in the list by ID number, starting from the lowest up and tries to set it as the leader.  Once a device is successfully set as a leader, it updates its device list and sets itself as the leader for all registered devices.  Since the gateway always uses ID 0 and assigns increasingly higher numbers to new devices as they register, this algorithm should always result in the gateway leading.  However, since all devices are initialized with an ID of zero, they will act as their own leader until registering with the gateway.  This is trivial though, since an unregistered device won't be aware of any other devices and will therefore set its clock_offset value to zero on synchronization.

The leader process is actually run as a continuous daemon thread by all devices, regardless of whether or not they have actually been set as a leader.  When the process is run, the device checks to see whether its self.ID value matches its self.leader value.  If so, it performs the clock synchronization function described below.  If not, the lead() thread sleeps for 60 seconds (10 for the gateway since it's expected to lead), then checks again to see if it has become the leader while sleeping.


CLOCK SYNCHRONIZATION:
----------------------

Clock synchronization is achieved vial a modified version of the Berkeley clock synchronization algorithm.  The leader asks each device for its current time, measuring the time it takes to receive a response.  This RTT is divided by two and added to the local time at which the leader sent the request to calculate the following device's clock offset.  Once all registered devices have been queried, the offsets are averaged together and pushed out to all devices to be summed with their previous offset values.


LOGICAL CLOCKS:
---------------
All functions which require message passing between devices require a clock value as an argument and return a clock value along with any other results.  When a device receives a clock value through a remote function call, it compares it to its own logical clock and updates its own value to one more than the maximum of the two.  Once the initiator receives the response, it does the same update process with the returned clock value, thereby making the two devices in sync with one another.


TEST CASES:
-----------

Since sensors will automatically generate randomized output, simply starting one (or more) of each device (in any order) and letting them run for a few minutes is sufficient for testing all implemented functionality.  Log files (or the history database) can be consulted to determine the sequence of system events and whether a given action had the expected results.


PERFORMANCE:
------------

When the temperature sensor's reading drops below 1 degree, the gateway turns on the outlet.  When it rises above 2 degrees, the outlet is turned off.

Changing the motion detection mode from HOME to AWAY and back again via both the user terminal and presence sensor was tested successfully.  In HOME mode, any motion triggers the gateway to turn on the bulb.  In away mode, an intruder alert message is printed and logged at both the gateway and the user device.

The bulb-auto shutoff feature was also tested by killing the motion program after it turned the bulb on.  After five minutes, the bulb automatically turned off.

The devices which rely on the server to query their state (e.g. temperature) seem to perform slightly faster than the push-only devices (e.g. motion), but the difference is only one or two milliseconds.

Adjusting the frequency of update requests and pushes doesn't seem to produce significant performance changes, indicating that this system does not place any excessive load on the EdLab machines.  Even removing all time.sleep() functions from every program (which produces the most frequent updates possible) does not introduce any latency.  From the time a device's state is set, it takes ~0.01 seconds for the change to be written to the persistent database.  Since this duration is on the order of the smallest time increment visible in the system's timestamps, it's impossible to tell how much of the delay is occurring at each tier.

The one time any latency does occur is when simultaneously launching a slew of different devices.  In this case, devices may take several seconds to register with the gateway (registering a single device happens almost instantaneously), but no messages are lost while the gateway processes the requests.

The addition of the features listed below may increase system overhead to the point where additional latency manifests, particularly at the gateway.


POTENTIAL IMPROVEMENTS:
-----------------------

The history database could be used as a checkpoint for the gateway to automatically reestablish old device registrations after recovering from a failure.

It may be possible to improve general performance by multi-threading additional functions.
 
There are many additional commands that could be handled by the user terminal, including:
	- GET(device_name): check the current state of a given smart device
	- SET(device_name, state): manually set the state of a given smart device
	- LIST: print a list of the currently registered devices to the user display
	- CLEAR: clear the gateway's list of currently registered devices (and potentially delete the registry file if one exists)
	- ORPHAN: initiate an orphan check (trigger the register() function at each previously registered address in a registry file)
	- REGISTER: manually re-register the user terminal
	- UNREGISTER(device_name): remove a given device from the gateway's registry by name
	- STATUS(device_name): check to see whether a given device is up and correctly registered
	- DISPLAY(message): print a given message to the user display
 
  
MISSING FEATURES:
-----------------

While clock synchronization, logical clocks, and persistent storage are all fully operational, I have not yet been able to leverage these features to take actions based on the ordering of events.  However, I found that this did not actually limit the system's capability to act autonomously.  While the system cannot determine the HOME/AWAY status solely from the order of motion and door sensor events, the same information is easily attained from the presence sensor alone.  Any time motion is detected or a door is opened, the presence sensor is queried.  If the user is not found to be present, an alert message is displayed.  While I recognize the value of event ordering and plan to implement it in future versions, it seems like an unnecessarily complex mechanism for detecting user presence when a simple sensor can achieve the same functionality with much less computational overhead and code complexity.


KNOWN ISSUESS:
--------------

None
