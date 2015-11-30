# Samuel DeLaughter
# 4/10/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
import xmlrpclib
import socket

from pprint import pprint
import logging
import shelve

import random
import time
import os


def similar(a, b):
#Check to see whether two values are "similar"
#Implemented by the user process to allow for case-insensitive input recognition

	a = (str(a)).lower
	b = (str(b)).lower
	return(a == b)
	
def setup_log(device_name):
#Prepare a log file named with the current timestamp and a given device name

	if not os.path.exists('logs'):
		os.makedirs('logs')
	t = time.localtime()
	timestamp = (str(t[0]) + '_' + str(t[1]) + '-' + str(t[2]) + '_' + str(t[3]) + '-' + str(t[4]) + '-' + str(t[5]))
	log_file = 'logs/' + str(timestamp) + '_' + str(device_name) + '.log'
	logging.basicConfig(filename=log_file, filemode='w', level=logging.DEBUG, format='%(levelname)8s | %(funcName)20s | %(message)s')

def get_gateway_address():
#Read the gateway's address from the gateway_ip.txt file
	read_address = False
	while not read_address:
		try:
			ip_file=open('gateway_ip.txt', 'r')
			with open('gateway_ip.txt', 'r') as f:
				address = str(f.readlines()[0])
			logging.debug('Read gateway address from file: ' + str(address))
			read_address = True
			return(address)
		except:
			logging.warning('Failed to read gateway address from file. Trying again in 10 seconds.')
			print('Failed to read gateway address from file Trying again in 10 seconds.')
			time.sleep(10)
		

def compose_address(ip, port):
#Compose a properly formatted address from an IP and Port number

	address = ('http://' + str(ip) + ':' + str(port))	
	return address

def build_receiver(device):
#Prepare an xmlrpc ServerProxy
#For executing a function on a remote device

	address = compose_address(device['ip'], device['port'])
	logging.debug('Building receiver with address: ' + str(address))
	r = xmlrpclib.ServerProxy(address, allow_none=True)
	return r
	
def gateway_connection():
	r = xmlrpclib.ServerProxy(get_gateway_address(), allow_none=True)
	return r

class device(object):
#The main class for all IOT devices, all other device classes inherit from this

	def __init__(self):
		self.id = '0'
		self.ip = socket.gethostbyname(socket.gethostname()) #Detect the local IP address
		self.name = 'device'
		self.port = 0
		self.state = 0
		self.clock = 0
		self.leader = '0'
		self.time_offset = 0
		
	def serve(self):
		self.server = SimpleXMLRPCServer((self.ip, self.port), logRequests=False, allow_none=True)
		self.server.register_function(self.ping)
		self.server.register_function(self.serve)
		self.server.register_function(self.register)
		self.server.register_function(self.timestamp)
		self.server.register_function(self.start_election)
		self.server.register_function(self.lead)
		self.server.register_function(self.get_time)
		self.server.register_function(self.set_time)		
		self.server.register_function(self.get_attr)
		self.server.register_function(self.set_attr)
		self.server.register_function(self.db_put)
		self.server.register_function(self.db_get_state)
		self.server.register_function(self.db_get_history)
		self.server.register_function(self.set_leader)
		self.server.register_function(self.devices_by_name)
		self.server.register_function(self.update_device_list)
		
		self.clock += 1
		try:
			print '\nStarting Server'
			print 'Use Control-C to exit'
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Starting Server')
			self.server.serve_forever()
		except KeyboardInterrupt:
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received keyboard interrupt, stopping server')
			print 'Exiting'
		
	def update_clock(self, c):
	#Update own logical clock by comparing it with a given clock value
	
		self.clock = (max(self.clock, c) + 1)
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Updated clock value to ' + str(self.clock))
		
	def timestamp(self):
	#Return the current time plus own time offset
	#Used for logging and database values
	
		return (time.time() + self.time_offset)
	
	def ping(self, c):
	#Return a dictionary of a device's own attributes and their values
	#Generally called by a remote device to see if a device in its list is still live
	
		self.update_clock(c)
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received ping, returning current state: ')
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + vars(self))
		return (self.clock, vars(self))
		
	def serve(self):
	#Start an xmlrpc server to listen for requests from other devices
	#Can be stopped by the standard Ctl-C keyboard interrupt (doing so will also kill the main thread)
	
		self.clock += 1
		try:
			print 'Use Control-C to exit'
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Starting Server')
			self.server.serve_forever()
		except KeyboardInterrupt:
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received keyboard interrupt, stopping server')
			print 'Exiting'
	
	def devices_by_name(self, name):
	#Find all devices in self.devices with a given name
	
		device_list = []
		for i in self.devices:
			if(self.devices[i]['name'] == name):
				device_list.append(self.devices[i])
		return device_list
	
	def get_attr(self, c, attr):
	#Return the value associated with a given attribute, if it exists
	#Generally called remotely
	
		self.update_clock(c)
		if(not(hasattr(self, attr))):
			logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Missing attribute ' + str(attr) + ' was queried, returning None')
			print('WARNING: Missing attribute ' + str(attr) + ' was queried, returning None')
			return self.clock, None
		else:
			v = (getattr(self, attr))
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received request for attr: ' + str(attr) + ', returning value: ' + str(v))
			return self.clock, v
		
	def set_attr(self, c, attr, val):
	#Set the value of a given attribute
	#Generally called remotely
	
		self.update_clock(c)
		setattr(self, attr, val)
		logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Attribute ' + str(attr) + ' was set to: ' + str(val))
		print('Attribute ' + str(attr) + ' was set to: ' + str(val))
		if((attr == 'state') and (not(self.name == 'backend'))):
			self.db_put(self.name, val)
		return self.clock
		
	def register(self):	
	#Register with the gateway, then initiate a leader election
		
		#Attempt to register with the gateway every 10 seconds until successful
		registered = False
		while not registered:
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Attempting to register with the gateway')
			try:
				self.clock += 1
				gateway = xmlrpclib.ServerProxy(get_gateway_address(), allow_none=True)
				c, self.id, self.port = gateway.register_device(self.clock, self.name, self.ip)
				self.update_clock(c)
				logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Registered with gateway. Using port number: ' + str(self.port))
				print('Registered with gateway. Using port number: ' + str(self.port))
				registered = True
			except:
				logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to register with the gateway, trying again in 10 seconds')
				print('WARNING: Failed to register with the gateway, trying again in 10 seconds')
				time.sleep(10)
				
		#Initiate a Leader Election
		self.clock += 1
		self.start_election()
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'New leader ID: ' + str(self.leader))
		print('New leader ID: ' + str(self.leader))
	
	def update_device_list(self):
	#Make sure self.devices is up to date
	
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Updating device list')
		if self.name == 'gateway':
		#If run on the gateway: ping each device in list to see if it's still live and remove any that can't be contacted
			for i in self.devices:
				try:
					self.clock += 1
					r = build_receiver(self.devices[i])
					c, self.devices[i] = r.ping(self.clock)
					self.update_clock(c)
				except:
					logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Removing device from list: ' + str(self.devices[i]))
					del(self.devices[i])
					self.clock += 1
		else:
		#If run on a non-gateway device: get the gateway's device list and update self.devices by comparison
			try:
				self.clock += 1
				gateway = xmlrpclib.ServerProxy(get_gateway_address(), allow_none=True)
				c, device_list = gateway.get_attr(self.clock, 'devices')
				self.update_clock(c)
				if(not(hasattr(self, 'devices'))):
				#If self.devices doesn't exist yet, initialize it as an empty dictionary
					self.devices = {}
				for i in device_list:
					self.devices[i] = device_list[i]
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Updated device list from gateway: ' + str(self.devices))
			except:
			#If the gateway can't be contacted, re-register
				self.clock += 1
				logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to update device list from gateway, re-registering')
				print('WARNING: Failed to update device list from gateway, re-registering')
				self.register()
		
	def start_election(self):
	#Start a leader election
	#Employes a modified bully alogrithm tailored to use the gateway as the leader whenever possible
	#Contacts each device in self.devices in ascending order by ID (gateway should always have id=0)
	#If a device can be contacted, set its leader to its own ID
	#Otherwise, remove it from the device list and try the device wiht the next-highest ID
	
		logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Starting Leader Election')
		print('Starting Leader Election')
		self.update_device_list()
		if(self.name == 'gateway'):
		#If run on the gateway, become
			self.set_leader(self.clock, self.id, self.id)
		else:
			assigned = False
			while not assigned:
				lowest = min(self.devices)
				r = build_receiver(self.devices[lowest])
				try:
					self.clock += 1
					c = r.set_leader(self.clock, lowest, self.id)
					self.update_clock(c)
					self.leader = lowest
					logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Set new leader with ID: ' + str(lowest))
					assigned = True
				except:
				
					del(self.devices[lowest])
					self.clock += 1
					logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Removed device from list: ' + str(lowest))
				
	def set_leader(self, c, val, initiator_id):
	#A special version of set_attr for modifying self.leader
	#First, get an updated device list from the gateway
	#Then, set the leader attribute of every device in self.devices to self.id
	#Skip self.id and the device that initiated this request, or else deadlock will occur
	#If any devices cannot be set, remove them from the list
	
		self.update_clock(c)
		self.leader = val
		if(val == self.id):
			self.db_put('leader', self.id)
			self.update_device_list()
			expired_devices = []
			for i in self.devices:
				if(not((i == self.id) or (i == initiator_id))):
					try:
						self.clock += 1
						r = build_receiver(self.devices[i])
						follower_clock = r.set_attr(self.clock, 'leader', self.id)
						self.update_clock(follower_clock)
						logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Set self as leader for device: ' + str(self.devices[i]))
					except:
						expired_devices.append(i)
						logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Flagged device for removal: ' + str(self.devices[i]))
			for i in expired_devices:
				self.clock += 1
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Removing device from list: ' + str(self.devices[i]))
				del(self.devices[i])
				
	def lead(self):
	#Act as a leader for clock synchronization between devices
	#This function is actually run by all devices continously (via a daemon thread), but does nothing unless self.leader == self.id
	#If this condition is met, use a modified berkeley clock synchronization algorithm to deliver clock_offset values to all known devices
	#If not, sleep for a minute (10 seconds if it's the gateway), then check to see if it's become the leader while asleep
	#The gateway sleeps for a shorter time period because it is expected to always server as the leader
	
		while 1:
			if(self.leader == self.id):
				self.update_device_list()
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Acting as leader...')
				t = {}
				rtt = {}
				offset = {}
				expired_devices = []
				for i in self.devices:
					if(not(i == self.id)):
						try:
							self.clock += 1
							r = build_receiver(self.devices[i])
							start = (time.time() + self.time_offset)
							c, t = r.get_time(self.clock)
							self.update_clock(c)
							end = (time.time() + self.time_offset)
							rtt = (end - start)
							offset[i] = (t - (start + (rtt / 2)))
						except:
							expired_devices.append(i)
							logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Flagged device for removal: ' + str(self.devices[i]))
				for i in expired_devices:
					self.clock += 1
					logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Removing device from list: ' + str(self.devices[i]))
					del(self.devices[i])
				
				#Calculate the average time offset for all active devices	
				offsets = [0]
				for i in offset:
					offsets.append(offset[i])
				average_offset = (sum(offsets) / len(offsets))
				
				expired_devices = []
				for i in self.devices:
					if(not(i == self.id)):
						try:
							self.clock += 1
							r = build_receiver(self.devices[i])
							c = r.set_time(self.clock, average_offset)
							self.update_clock(c)
						except:
							expired_devices.append(i)
							logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Flagged device for removal: ' + str(self.devices[i]))
				for i in expired_devices:
					self.clock += 1
					logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Removing device from list: ' + str(self.devices[i]))
					del(self.devices[i])
				self.time_offset += average_offset
				self.clock += 1
				time.sleep(30)
			else:
				if(self.name == 'gateway'):
					self.clock += 1
					time.sleep(10)
				else:
					self.clock += 1
					time.sleep(60)
				
	def get_time(self, c):
	#Return the current local time plus self.time_offset
	#Called remotely by the leader when synchronizing
	
		self.update_clock(c)
		return(self.clock, (time.time() + self.time_offset))
		
	def set_time(self, c, offset):
	#Set self.time_offset
	#Called remotely by the leader when synchronizing
	
		self.update_clock(c)
		self.time_offset += offset
		return self.clock
	
	def db_put(self, k, v):
	#Contact the backend device to store a value in the persistent databases
	
		dbs = self.devices_by_name('backend')
		for db in dbs:
			self.clock += 1
			r = build_receiver(db)
			c = r.db_put(self.clock, k, v)
			self.update_clock(c)
			
	def db_get_state(self, k):
	#Contact the backend device to retrieve a value from the persistent state database
	
		dbs = self.devices_by_name('backend')
		values = []
		for db in dbs:
			self.clock += 1
			r = build_receiver(db)
			c, v = r.db_get_state(self.clock, k)
			self.update_clock(c)
			values.append(v)
		return values
	
	def db_get_history(self, k):
	#Contact the backend device to retrieve a value from the persistent history database
	
		dbs = self.devices_by_name('backend')
		values = []
		for db in dbs:
			self.clock += 1
			r = build_receiver(db)
			c, v = r.db_get(self.clock, k)	
			self.update_clock(c)
			values.append(v)
		return values
	
	'''
	#These two functions are not currently implemented anywhere, but could be useful for push-based sensors
	def send_state(self, device):
	#Push the current state to a given device
	
		try:
			r = build_receiver(device)
			c = r.receive_state(self.clock, self.state)
			self.update_clock(c)
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Sent state to device:\n' + str(device))
		except:
			logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed sending state to device:\n' + str(device))
			print('WARNING: Failed sending state to device:\n' + str(device))
		
	def receive_state(self, c, device):
	#Receive a push request from a given device and update self.devices to reflect the change
	
		self.update_clock(c)
		if(not(hasattr(self, 'devices'))):
			self.devices = {}
		self.devices[device['id']] = vars(device)
		return self.clock
	'''
