#Samuel DeLaughter
#3/16/15


ABOUT:
------------

This is a distributed system simulating a home "internet-of-things" network which employs temperature and motion sensors to manage a smart bulb and smart outlet via a gateway.  It consists of the following seven python programs, located in the resources folder:

gateway.py
bulb.py
outlet.py
temp.py
motion.py
user_display.py
user_terminal.py

These programs can be distributed across as many or as few different machines as desired, as long as those machines are all networked and capable of communicating with one another by IP addresses with port numbers in the 9000-9006 range.

All programs are written in pure python (tested on version 2.7.3), and require no external libraries.  The xmlrpclib and SimpleXMLRPCServer modules are used for inter-device communication.

Devices can be started in any order, though it's most efficient to start the gateway first.  This prevents unnecessary overhead as the devices repeatedly fail in attempting to contact the gateway for registration.  Any device can be stopped (with the standard Ctl-C keyboard interrupt command) and restarted with no adverse effects -- it will be reregistered at the gateway and given the same ID number it had previously.  However, devices which do not actively push to the gateway have no mechanism to check whether it's still up.  Thus, if the gateway goes down it's good practice to restart all other devices (some will be unresponsive otherwise).

The user process is split into two: a display and terminal for output and input, respectively.  The terminal process does nothing but prompt for an handle user input, namely to change the mode of the motion-detection function to either HOME or AWAY.  The display process will show confirmation of these changes, as well as an alert message if an intruder is detected.

Each program will record detailed logs in a 'logs' folder, created in the same folder as the program.  Whenever a program is started, its old log file will be erased.



CONFIGURATION:
-------------

Devices are started simply by running each program in its own terminal window as follows:
cd /path/to/resources/
python device_name.py

When each sensor, smart device, and user device starts up, it must check the gateway_ip.txt file in order to contact the gateway for registration. When the gateway starts, it writes its address to this file automatically.  Therefore, if the seven programs can all share the same gateway_ip.txt file, no manual configuration is necessary.  This feature works particularly well on EdLab, since even if the devices are running on separate machines, the gateway_ip.txt file will be replicated to all of them as soon as the gateway process writes to it.

If this replication does not or cannot occur, the gateway_ip.txt file must be written to manually before any devices will be able to register with the gateway.  It must contain only the gateway's network address, formatted as follows on a single line:

http://ip:port

For example:
http://127.0.0.1:9000

Without replication, it's safest to start the gateway first and then manually copy the gateway_ip.txt file to the other machines -- this will ensure that the address is both accurate and properly formatted.

The included gateway_ip.txt file currently contains the address of elnux1.cs.umass.edu, where the gateway program was last run.  By default the gateway is set up to use port 9000, and it has not been tested with any other port numbers.



DESIGN DECISIONS:
----------------

 - The gateway is multi-threaded by necessity: one daemon thread queries the temperature sensor every five seconds, a second one handles the bulb's auto-shutoff feature, and the main thread listens for and handles requests from other devices.

 - Though the auto-shutoff process is implemented as a continously running daemon thread, it's intelligent enough to spend most of its time sleeping.  This is achieved by comparing the current on-time of the bulb with the maximum on-time (300 seconds), then sleeping for the difference between the times before re-checking.



PERFORMANCE:
-----------

The sample_output folder contains copies of logs recorded during a period of operation which tested a number of different features.  Devices were brought online in a random order (some before the gateway), and all were able to register once the gateway came online.  Some devices were forcibly restarted, and were able to reregister with the gateway and receive the same ID/Port number.  Since log files are overwritten on each run, logs from before the devices were restarted are not shown.

When the temperature sensor's reading drops below 1 degree, the gateway turns on the outlet.  When it rises above 2 degrees, the outlet is turned off.

Changing the motion detection mode from HOME to AWAY and back again via the user terminal was tested successfully.  In HOME mode, any motion triggers the gateway to turn on the bulb.  In away mode, an intruder alert message is printed and logged at both the gateway and the user terminal.

The bulb-auto shutoff feature was also tested by killing the motion program after it turned the bulb on.  After five minutes, the gateway automatically signaled the bulb to turn off.  After this point the motion device was manually restarted, causing its earlier log to be erased.

The devices which rely on the server to query their state (e.g. temperature) seem to perform slightly faster than the push-only devices (e.g. motion), but the difference is only one or two milliseconds.  This may be attributable to the fact that the temperature-checking function runs in its own thread, though I have not done the tests necessary to confirm this explanation.

Adjusting the frequency of update requests and pushes doesn't seem to produce significant performance changes, indicating that this system does not place any excessive load on the EdLab machines.  Even removing all time.sleep() functions from every program (which produces the most frequent updates possible) does not introduce any latency.  The gateway occasionally fails to set the bulb's state under these conditions, but only because it sends a second update quicker than the first can be completed.

The addition of the features listed below may increase system overhead to the point where latency manifests, particularly at the gateway.



POTENTIAL IMPROVEMENTS:
----------------------

 - The gateway has no mechanism to check for orphaned processes.  Since certain processes do not routinely contact the gateway on their own, they must be restarted manually anytime the gateway restarts.  An orphan check could theoretically be implemented by having the gateway write addresses to a registry file each time a new device is registered, and checking this file on startup.
  
 - Since the bulb's auto-shutoff mechanism is handled by the gateway, it will stay on indefinitely if communication with the gateway fails.  It would be preferable to manage this function locally in the bulb process, though this would require multithreading which would complicate the process (currently only the gateway is multithreaded).
 
 - It's likely possible to improve general performance by multi-threading programs other than the gateway.
 
 - It may be helpful to create a new log file for each run rather than overwriting the old one.  However, the file size of certain logs can get quite large if their device runs for an extended period of time.
 
 - It is currently impossible to register more than one device with the same name -- if two temperature devices attempt to register from different addresses, they will compete endlessly for the same ID/Port number.  Changing this would require modifications to several functions in the gateway program, specifically making id_from_name() return a list rather than an integer, and making the functions which rely on it capable of handling a list of IDs.
 
 - There are many additional commands that could be handled by the user terminal, including:
  	- GET(device_name): check the current state of a given smart device
 	- SET(device_name, state): manually set the state of a given smart device
  	- LIST: print a list of the currently registered devices to the user display
 	- CLEAR: clear the gateway's list of currently registered devices (and potentially delete the registry file if one exists)
 	- ORPHAN: initiate an orphan check (trigger the register() function at each previously registered address in a registry file)
 	- REGISTER: manually re-register the user terminal
 	- UNREGISTER(device_name): remove a given device from the gateway's registry by name
 	- STATUS(device_name): check to see whether a given device is up and correctly registered
 	- DISPLAY(message): print a given message to the user display
 	
 
  
 KNOWN ISSUES:
------------
 
 - Occasionally, killing and restarting a device may yield a socket error stating that the address is already in use.  This error occurs after the device successfully registers with the gateway, but is inconsistent and quite rare.  The only apparent solution is to completely stop all devices in the system and close their terminal windows before restarting