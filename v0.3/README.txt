# Samuel DeLaughter
# 4/10/15


ABOUT:
------

This is a distributed system simulating a home "internet-of-things" network composed of a gateway, backend database, and user terminal, along with several sensors and smart devices.


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
		The backend tier -- manages the persistent databases
		
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
		
		
All device files rely on iot.py for the generic device class definition, as well as some helper functions.  While only this file, the start script, and gateway_list.txt (explained later) are required to be present for a device's python script to run, it's best practice to place a copy of the entire resources file on each machine that will be used.  Note that this is a trivial requirement when running the system on the edLab machines, since all files will be automatically replicated between all machines.

Devices can be started in any order, though it's most efficient to start the gateway first.  If another device is started first, it will repeatedly attempt to register with the gateway (and fail) every ten seconds, generating unnecessary overhead.  It's also wise to start the backend device early in the sequence (perhaps even before the gateway), or else some system events will be missing from the database files.

Any device can be stopped (using the standard Ctl-C keyboard interrupt command) and restarted with no adverse effects -- it will select a new gateway at random and be reregistered with a new ID number.  Certain functions on the gateway will check for dead devices in the registration list and delete them when found.  Their port numbers will be recycled, but never their IDs.

Backend devices rely on a daemon thread (gateway_heartbeat) to periodically make sure it's still running.  This simply attempts to trigger the gateway's ping function no mechanism to check whether it's still up.  If not, they will select a new gateway address at random from gateay_list.txt and try to register there.


CONFIGURATION:
-------------

When each non-gateway device starts up, it must check the gateway_list.txt file in order to contact a gateway for registration. When a gateway starts, it writes its address to this file automatically.  Therefore, if the programs can all share the same gateway_list.txt file, no manual configuration is necessary.  This feature works particularly well on EdLab, since even if the devices are running on separate machines, the gateway_list.txt file will be replicated to all of them as soon as the gateway process writes to it.

If this replication does not or cannot occur, or if the file is deleted after a gateway has written to it, the gateway_list.txt file must be written manually before any devices will be able to register with a gateway.  It must contain only the gateway's network address, formatted as follows on a single line:

http://ip:port

For example:
http://127.0.0.1:9000

Without replication, it's safest to start a gateway first and then manually copy the gateway_list.txt file to the other machines -- this will ensure that the address is both accurate and properly formatted.

By default the gateway is set up to use port 9000, though this number can be set with the self.port attribute in the __init__ function for the gateway() class in gateway.py.

When a gateway device starts up, it first checks to see if the gateway_list.txt file is empty.  If so, it writes its own address to the file and starts a server to listen for requests.  If not, it attempts to contact each address in the file until it finds one with which it can register.  The gateway it registers with then assigns it an ID number and a port to listen on, and appends its address to gateway_list.txt.


DESIGN:
-------
All device files are written in pure python (tested on version 2.7.3), and require no external libraries.  Python's xmlrpclib and SimpleXMLRPCServer modules are used for inter-device communication.  The execution file is a simple bash script.

The python scripts are highly object-oriented; each different device type has its own class, a new instance of which is created at the start of the main() function.

Device files can be distributed across as many or as few different physical machines as desired, as long as those machines are all IP-routable.  Each device on the same IP address gets a unique port number, starting at 9001 (the gateway always uses port 9000 no matter what other devices may be using its IP).

Any number of devices of the same type can be run simultaneously.  However, the gateway does not have the intelligence to -- for example -- assign a specific temperature sensor to a specific outlet.  Rather, devices with the same name are effectively grouped.  All outlets are turned on or off together, as are bulbs.  Temperature values are collected from all registered temperature sensors and averaged.  If any one presence sensor's state changes, the motion detection mode will change accordingly.  Whenever motion is detected by any motion sensor, the gateway will take appropriate action based on the current motion mode.  Only one instance of the gateway should ever be running at any given time, and the system has never been tested with multiple backend devices.

Since no actual sensor hardware is available for this project, sensor processes implement naive sense() functions whenever their states are queried.  Temperature sensors randomly return an integer between -20 and 40.  Motion sensors have a 1/4 chance of changing their state each time their sense() function is run, and report to the gateway whenever their state is 1.  Presence sensors also have a 1/4 chance of changing their state each time their sense() function is run, but only report to the gateway when their state actually changes.

The user process is split into two separate devices, a terminal and a display.  If they were combined, displaying an alert message would require getting a lock to interrupt the user input thread.  When the user enters a command into the terminal device, the results will be printed to the display device.  However, if the user enters an invalid command, a list of valid commands will be displayed directly at the terminal before initiating the next input prompt.

All device processes are multi-threaded, but no locks are implemented.  Rather, the sending of messages is designed in a way that should naturally avoid any potential deadlock scenarios.  If device A triggers a remote script on device B, that script will never attempt to contact A before returning a response to the original request.


REPLICATION:
------------
The gateway and backend devices now support replication.  When a gateway starts up (once it's either completed registration with another gateway or written its address to gateway_list.txt), it creates a new file in the db_requests folder, named with its current timestamp (prepended with 'req_' to avoid confusion with temporary and hidden files).  The sole contents of this file are its ip address and port number, on separate lines.

When a new backend device starts up, it checks the list of files in the db_requests folder.  It reads the ip and port values from the oldest file (determined by checking for the minimum value of all the filenames).  It then attempts to trigger that register_db function at that address.  If successful, it receives an id and port number just like a regular device would upon registering.

Once a gateway has registered a backend device, it deletes its request file and rejects all other requests.  If it ever detects that its backend device has failed, it creates a new request file.

Consistency is implemented as Read-Once Write-All.  Whenever a gateway writes to its database, it also informs any other gateways that they should write the same value to their databases.  That way, gateways can all perform reads from their own databases and still get up-to-date information for the whole system.


CACHING:
--------
Whenever a gateway writes something to its database, it first writes it to its cache.  When a gateway wants to check a state value for a device, it only polls its database in the case of a cache miss.  When checking a history item, it goes straight to the database since the cache is unlikely to have retained historical information, and the key-value structure of the request would make performing such a check exceedingly difficult.

The caches have a fixed length which can be configured in the gateway class's __init__ function -- the default value is 100.  This is enforced as follows:
 - The cache is structured as an ordered dictionary (collections.OrderedDict)
 - When a new item is added to the cache, it's added as the first item, and the last item is removed
 - When an item is read from the cache, it's popped out and reinserted as the first item to make it available longer.
 
 
FAULT TOLERANCE:
----------------
Gateways have a cleanup function to facilitate a graceful shutdown in the case of a Keyboard Interrupt.  If a gateway has an unresolved database request file, it will delete it.  It will also delete its own address from gateway_list.txt, and inform any other gateways that it should be removed from their list of devices.

Aside from these cleanup tasks, fault tolerance is primarily handled by devices rather than gateways.  If a device detects that its gateway is no longer responsive, it will pick a new address at random from gateway_list.txt and reregister.  Since all writes at one gateway are immediately replicated to all others, no information should be lost in this process.  However, if only a single gateway is running with no replication, all information will be lost when it crashes.  Devices will still attempt to reregister until a new gateway comes on line, but it will not be able to recover any of their states or histories.  


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



LOGICAL CLOCKS:
---------------
Since removing logical clocks from the system would've required modifying nearly every function and function call for every device, I found it easier to leave them in.

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
None


KNOWN ISSUES:
--------------
On rare occasions, the gateway's cleanup function may fail to delete its entry from gateway_list.txt.  This file must be empty before starting up the first gateway (DO NOT delete the file, the gateways will not recreate it).  Otherwise, the new gateway will perpetually attempt to register with non-existent gateways at the stale addresses instead of writing its own address to file and starting a server .