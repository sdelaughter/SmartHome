#Samuel DeLaughter
#3/16/15

from SimpleXMLRPCServer import SimpleXMLRPCServer
from multiprocessing import Process
from threading import Thread
from pprint import pprint
from time import sleep
import xmlrpclib
import logging
import socket
import time
import os

SELF_PORT = 9000
DEVICE_ID = SELF_PORT
devices={}
BULB_LAST_ON = time.time()
MOTION_MODE = 'HOME'

def status():
	return True


def register(device_type, name, ip):
#Allow a device to register itself with the gateway
#Return an integer ID number to be used as a port number for the device to listen on

	global devices
	global SELF_PORT
	
	#If a device with the same name is already registered, overwrite it and return the existing ID/Port number
	port=id_from_name(name)
	if(port in devices):
		old_device=devices[port]
		address = ('http://' + str(ip) + ':' + str(port))
		devices[port]={'type': device_type, 'name': name, 'address': address}
		print('\nRe-registered ' + str(name) + ' device')
		print('    old: ' + str(old_device))
		print('    new: ' + str(devices[port]))
		return(port)
		
	#If no devices are registered with the same name, generate and return a new ID/Port number
	else:
		global DEVICE_ID
		DEVICE_ID += 1
		port = DEVICE_ID
		address = ('http://' + str(ip) + ':' + str(port))
		device_info={'type': device_type, 'name': name, 'address': address}
		devices[port] = device_info
		print('\nRegistered new device with id = ' + str(port) + ':')
		print(devices[port])
		return(port)

def unregister(id):
#Remove a device from the device list without modifying the registry file

	global devices
	del devices[id]
			
def id_from_name(name):
#Check the device list for a given name, return the associated ID/Port number if found

	logging.debug('Trying id_from_name with name: ' + str(name))
	global devices
	for d in devices:
		if str(devices[d]['name']) == str(name):
			logging.debug('Returning id: ' + str(d))
			return d
	logging.debug('No ID found for name: ' + str(name) + ', returning ID: None')
	return None

def address_from_id(id):
#Check the device list for a given id and return the associated address

	logging.debug('Trying address_from_id with ID: ' + str(id))
	global devices
	if id == None:
		address = None
	elif(id in devices):
		address = devices[id]['address']
	else:
		address = None
	logging.debug('Returning address: ' + str(address))
	return address

def change_mode(mode):
#Set the motion-detection mode to either HOME or AWAY and alert the user of the change

	address=address_from_id(id_from_name('display'))
	global MOTION_MODE
	if((mode == 'AWAY') or (mode == 'HOME')):
		MOTION_MODE = mode
		logging.info('Mode changed to ' + str(mode))
		print('Mode changed to ' + str(mode))
		try:
			device = xmlrpclib.ServerProxy(str(address), allow_none=True)
			message='Mode was changed to ' + str(mode)
			device.display(message)
		except:
			logging.warning('Could not connect to the display device at ' + str(address))
			print('\nWARNING: Could not connect to the display device at ' + str(address))
		return('Done')
	elseP
		
def current_mode():
#Return the current motion-detection mode

	global MOTION_MODE
	return MOTION_MODE

def query_state(name):
#Query a device with the given name for its current state

	address=address_from_id(id_from_name(name))
	if address == None:
		logging.warning('query_state failed, no registered device with name: ' + str(name))
		print('\nWARNING: query_state failed, no registered device with name: ' + str(name))
		return None
	else:
		try:
			device = xmlrpclib.ServerProxy(str(address), allow_none=True)
			logging.debug('Querying device: ' + str(name))
			state = device.get_state()
			logging.debug('Got state: ' + str(state))
			return state
		except:
			logging.warning('Could not connect to the ' + str(name) + ' device at ' + str(address))
			print('\nWARNING: Could not connect to the ' + str(name) + ' device at ' + str(address))
			
def change_state(name, state):
#Change the state of a given device

	address=address_from_id(id_from_name(name))
	if address == None:
		logging.warning('change_state failed, no registered device with name: ' + str(name))
		print('\nWARNING: change_state failed, no registered device with name: ' + str(name))
		return
	else:
		try:
			device = xmlrpclib.ServerProxy(str(address), allow_none=True)
			logging.debug('Setting state of ' + str(name) + ' device to: ' + str(state) + '...')
			device.set_state(state)
			logging.debug('Success')
			return
		except:
			print('\nCould not connect to the device at: ' + str(address))
			print('                        with state: ' + str(state))
		
def check_temp():
#Check the current temperature

	logging.debug('Checking temperature...')
	temp = query_state('temperature')
	logging.debug('Received value of: ' + str(temp))
	if(temp < 1):
		logging.debug('Temperature is below 1 degree, turning outlet on')
		change_state('outlet', 1)
	elif(temp > 2):
		logging.debug('Temperature is above 2 degrees, turning outlet off')
		change_state('outlet', 0)
	else:
		logging.warning('Anomolous temperature value received')
		return
		
def alert_user():
#Send an intruder alert to the user display

	address=address_from_id(id_from_name('display'))
	if address == None:
		logging.warning('alert_user failed, no registered users' + str(name))
		print('\nWARNING: alert_user failed, no registered users')
		return None
	else:
		try:
			device = xmlrpclib.ServerProxy(str(address), allow_none=True)
			device.intruder_detected()
			logging.debug('User Alerted')
			print('User Alerted')
		except:
			logging.warning('Could not connect to the display device at ' + str(address))
			print('\nWARNING: Could not connect to the display device at ' + str(address))

def motion_reported():
#Triggered by the motion sensor when it detects motion

	#If the current mode is HOME, turn on the bulb
	if MOTION_MODE == 'HOME':
		logging.debug('Motion detected, turning bulb on')
		change_state('bulb', 1)
		global BULB_LAST_ON
		BULB_LAST_ON = time.time()
	else:
	#If the current mode is anything but HOME, send an intruder alert to the user
		print('\n!!!!!!!!!!!!!!!!!!!!!!!!!')
		print('!!! INTRUDER DETECTED !!!')
		print('!!!!!!!!!!!!!!!!!!!!!!!!!\n')
		logging.critical('!!!!!!!!!!!!!!!!!!!!!!!!!')
		logging.critical('!!! INTRUDER DETECTED !!!')
		logging.critical('!!!!!!!!!!!!!!!!!!!!!!!!!')
		alert_user()
			
def start_server(server):
#Listen for requests from other devices
	try:
		print 'Use Control-C to exit'
		logging.info('Starting Server')
		server.serve_forever()
	except KeyboardInterrupt:
		logging.info('Received keyboard interrupt, stopping server')
		print 'Exiting'
		
def monitor_temp():
#The main client function.  Queries the temperature sensor every 5 seconds
	while True:
		global devices
		if id_from_name('temperature') in devices:
			check_temp()
		sleep(5)
		
def bulb_auto_shutoff():
#Checks periodically to see if the bulb has been on for over 5 minutes, and if so turns it off
	max_time = 300
	while True:
		global devices
		if id_from_name('bulb') in devices:
			global BULB_LAST_ON
			if BULB_LAST_ON == False:
				sleep(5)
				pass
			else:
				duration = time.time() - BULB_LAST_ON
				if duration >= max_time:
					logging.debug('Bulb was last turned on over 5 minutes ago, turning it off now')
					change_state('bulb', 0)
					BULB_LAST_ON = False
					sleep(max_time)
				elif(0 <= duration <= max_time):
					logging.debug('Bulb was turned on ' + str(duration) + ' seconds ago, checking again in ' + str(max_time-duration) + ' seconds')
					sleep(max_time-duration)
				else:
					logging.warning('Anomolous bulb-on duration, resetting last-on value and checking again in 5 minutes')
					BULB_LAST_ON = time.time()
					sleep(max_time)
		else:
			sleep(5)


def main():
	#Set up logging
	logging.basicConfig(filename='logs/gateway.log', filemode='w', level=logging.DEBUG, format='%(asctime)s.%(msecs)3d | %(levelname)8s | %(funcName)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
	
	#Detect local address and write to gateway_ip file
	SELF_IP = socket.gethostbyname(socket.gethostname())
	ip_file=open('gateway_ip.txt', 'w')
	ip_file.write(str(SELF_IP) + ':' + str(SELF_PORT))
	ip_file.close()
	
	#Initialize the server and make its functions available
	server = SimpleXMLRPCServer((SELF_IP, SELF_PORT), logRequests=False, allow_none=True)
	server.register_function(register)
	server.register_function(unregister)
	server.register_function(current_mode)
	server.register_function(change_mode)
	server.register_function(query_state)
	server.register_function(change_state)
	server.register_function(check_temp)
	server.register_function(motion_reported)
	server.register_function(status)

	#Initialize and start daemon threads for checking temperature and automatically shutting off the bulb
	temp_thread=Thread(target=monitor_temp, name='Gateway-Temp-Process')
	temp_thread.daemon=True
	bulb_thread=Thread(target=bulb_auto_shutoff, name='Gateway-Bulb-Process')
	bulb_thread.daemon=True
	temp_thread.start()
	logging.info('Started Temperature Monitoring Process')
	bulb_thread.start()
	logging.info('Started Bulb Auto-Shutoff Process')
	
	#Start the main server
	start_server(server)
	
	
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		os.exit()
