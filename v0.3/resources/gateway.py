# Samuel DeLaughter
# 5/8/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import xmlrpclib
import socket
import time
import os

import collections
import logging

import iot

        
class gateway(iot.device):
#The class defining gateway devices

	def __init__(self):
		iot.device.__init__(self)
		self.name = 'gateway'
		self.category = 'gateway'
		
		#Set up logging
		start_time=time.localtime()
		iot.setup_log(self.name, start_time)
		
		self.port = 9000
		self.door_state = 0
		self.motion_mode = 'HOME'
		self.temperature_interval = 10
		
		self.cache_capacity = 100
		self.cache = collections.OrderedDict()
		
		self.backend_ip = False
		self.backend_port = False
		
		self.register()
		self.request_db()
		
		'''
		#Initialize and start daemon thread for serving as the clock synchronization leader
		leader_thread=Thread(target=d.lead, name='Bulb Leader Thread')
		leader_thread.daemon = True
		leader_thread.start()
		'''
		
		#Initialize and start daemon threads for checking temperature and automatically shutting off the bulb
		#temp_thread=Thread(target=self.monitor_temperature, name='Gateway Temperature Thread')
		#temp_thread.daemon = True
		#temp_thread.start()
		
		self.serve()
		
		
	def serve(self):
		self.server = SimpleXMLRPCServer((self.ip, self.port), logRequests=False, allow_none=True)
		self.server.register_function(self.ping)
		self.server.register_function(self.serve)
		self.server.register_function(self.register)
		self.server.register_function(self.timestamp)
		#self.server.register_function(self.start_election)
		#self.server.register_function(self.lead)
		#self.server.register_function(self.get_time)
		#self.server.register_function(self.set_time)		
		self.server.register_function(self.get_attr)
		self.server.register_function(self.set_attr)
		self.server.register_function(self.db_put)
		self.server.register_function(self.db_get_state)
		self.server.register_function(self.db_get_history)
		#self.server.register_function(self.set_leader)
		self.server.register_function(self.device_by_name)
		self.server.register_function(self.devices_by_name)
		self.server.register_function(self.update_device_list)
		
		self.server.register_function(self.cache_put)
		self.server.register_function(self.cache_get)
		self.server.register_function(self.db_update)
		self.server.register_function(self.register_db)
		self.server.register_function(self.add_device)
		self.server.register_function(self.remove_device)
		self.server.register_function(self.register_device)
		self.server.register_function(self.handle_temperature)
		self.server.register_function(self.monitor_temperature)
		self.server.register_function(self.alert_user)
		self.server.register_function(self.handle_motion)
		self.server.register_function(self.handle_door_state)
		#self.server.register_function(self.monitor_presence)
		
		self.clock += 1
		try:
			print '\nStarting Server at ' + str(self.address())
			print 'Use Control-C to exit'
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Starting Server at ' + str(self.address()))
			self.server.serve_forever()
		except KeyboardInterrupt:
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received keyboard interrupt')
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Running cleanup function')
			self.cleanup()
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Stopping server')
			print 'Exiting'
	
	
	def address(self):
		return iot.compose_address(self.ip, self.port)
		 
	
	def register(self):
		self.ip = socket.gethostbyname(socket.gethostname())
		with open('gateway_list.txt', 'r') as f:
			addresses = f.readlines()
		if(addresses == []):
			self.clock += 1
			with open('gateway_list.txt', 'w') as f:
				f.write(str(self.address()) + '\n')
			self.devices[self.id] = {'name': self.name, 'category': self.category, 'ip': self.ip, 'port': self.port}
		elif(str(self.address()) in addresses):
			try:
				g = xmlrpclib.ServerProxy(self.address(), allow_none=True)
				c, self.id, self.port, self.devices = g.register_device(self.clock, self.name, self.ip)
				self.update_clock(c)
			except:
				self.devices[self.id] = {'name': self.name, 'category': self.category, 'ip': self.ip, 'port': self.port}
		else:
			registered = False
			while not registered:
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Attempting to register with the gateway')
				gw_address = iot.get_gateway_address()
				gateway = xmlrpclib.ServerProxy(gw_address, allow_none=True)
				try:
					self.clock += 1
					c, self.id, self.port, self.devices = gateway.register_device(self.clock, self.name, self.ip)
					self.update_clock(c)
					logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Registered with gateway. Using port number: ' + str(self.port))
					print('Registered with gateway. Using port number: ' + str(self.port))
					registered = True
				except:
					logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to register with the gateway, trying again in 10 seconds')
					print('WARNING: Failed to register with the gateway, trying again in 10 seconds')
					time.sleep(10)
		print('Registered with ID: ' + str(self.id) + ' and port: ' + str(self.port))
	
	
	def request_db(self):
		filename = ('db_requests/req_' + str(time.time()))
		f = open(filename, 'w')
		f.write(str(self.ip) + '\n')
		f.write(str(self.port))
		f.close()
		logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Wrote new database request with filename: ' + str(filename))
		self.request_name = filename
	
	
	def new_device(self, id, d):
	#Register a new device in self.devices
	#Notify all other gateways that they should register it too
		
		self.devices[id] = d
		gateways = self.devices_by_name('gateway')
		for i in gateways:
			address = iot.compose_address(i['ip'], i['port'])
			if('id' in i):
				if i['id'] == id:
					continue
			if(address == self.address()):
				continue
			try:
				g = xmlrpclib.ServerProxy(address, allow_none=True)
				c = g.add_device(self.clock, id, d)
				self.update_clock(c)
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Added device with ID ' + str(id) + ' to the gateway at ' + str(address))
			except:
				logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to add device with ID ' + str(id) + ' to the gateway at ' + str(address))
			
		
	def old_device(self, id):
	#Delete an old device from self.devices
	#Notify all other gateways that they should delete it too
		del(self.devices[id])
		gateways = self.devices_by_name('gateway')
		for i in gateways:
			try:
				if(id == i['id']):
					continue
			except:
				address = iot.compose_address(i['ip'], i['port'])
				if(address == self.address()):
					continue
				else:
					try:
						g = xmlrpclib.ServerProxy(address, allow_none=True)
						c = g.remove_device(self.clock, id)
						self.update_clock(c)
					except:
						logging.warning('Failed to remove device with ID ' + str(id) + ' from the gateway at ' + str(address))
	
	
	def add_device(self, c, id, d):
	#Add a new device to self.devices
		self.update_clock(c)
		self.devices[id] = d
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Added device with ID ' + str(id) + ' to list: ' + str(self.devices[id]))
		return self.clock
				
	
	def remove_device(self, c, id):
	#Delete a device from self.devices
		self.update_clock(c)
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Deleting device with ID ' + str(id) + ' from list: ' + str(self.devices[id]))
		del(self.devices[id])
		return self.clock()
		
	
	def next_port(self):
		ports = []
		for i in self.devices:
			if self.devices[i]['ip'] == self.ip:
				ports.append(self.devices[i]['port'])
		if(len(ports) == 0):
			port = self.port + 1
		else:
			port = (max(ports) + 1)
		return port
	
	
	def register_device(self, c, name, ip):
	#Allow a device to register itself with the gateway
	#Called remotely by devices when they start up or are unable to contact a previously registered gateway
	#Adds a new entry to the gateway's self.devices dictionary with the device's name, category, id, ip, and port number
	#Assigns the device a port number and instructs it which port to listen on
	#Devices with different IPs may share port numbers, but every device's port number will always be greater than the gateway port
	
		self.update_clock(c)
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received registration request from ' + str(name) + ' device at ' + str(ip))
		
		#Find the next available ID number
		id = str(int(max(self.devices)) + 1)
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Assigning new ' + str(name) + ' device id: ' + str(id))
		
		#Find the next available port number for the device's IP
		port = self.next_port()
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Assigning new ' + str(name) + ' device port number: ' + str(port))
		
		#Register the device's info in self.devices and return the updated list along with an id and port number
		d = {'id': id, 'name': name, 'ip': ip, 'port': port}
		self.new_device(id, d)
		self.clock += 1
		#print('Registered new device: ' + str(self.devices[id]))
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Registered new device: ' + str(self.devices[id]))
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Current Device List: ' + str(self.devices))
		
		if(name == 'gateway'):
		#If this is a gateway replica trying to register, append its address to gatway_list.txt
			with open('gateway_list.txt', 'a') as f:
				f.write('http://' + str(ip) + ':' + str(port) + '\n')
		
		return self.clock, id, port, self.devices
		
		
	def register_db(self, c, name, ip):
	#Allow a device to register itself with the gateway
	#Called remotely by devices when they start up or are unable to contact a previously registered gateway
	#Adds a new entry to the gateway's self.devices dictionary with the device's name, category, id, ip, and port number
	#Assigns the device a port number and instructs it which port to listen on
	#Devices with different IPs may share port numbers, but every device's port number will always be greater than the gateway port
	
		self.update_clock(c)
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received registration request from backend device at ' + str(ip))
		
		if((self.backend_ip == False) or (self.backend_port == False)):
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'No previously registered backend device, processing request...')

			#Find the next available ID number
			id = str(int(max(self.devices)) + 1)
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Assigning new ' + str(name) + ' device id: ' + str(id))
			
			#Find the next available port number for the device's IP
			port = self.next_port()
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Assigning new ' + str(name) + ' device port number: ' + str(port))
			
			#Register the device's info in self.devices and return the updated list along with an id and port number
			self.backend_ip = ip
			self.backend_port = port
			d = {'id': id, 'name': name, 'ip': ip, 'port': port}
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Adding new device: ' + str(d))
			self.new_device(id, d)
			self.clock += 1
			print('Registered new backend device: ' + str(self.devices[id]))
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Registered new backend device: ' + str(self.devices[id]))
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Current Device List: ' + str(self.devices))
			os.remove(self.request_name)
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Returning port: ' + str(port))
			return self.clock, id, port, self.devices
		else:
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Already registered a backend device. Removing old request: ' + str(self.request_name))
			os.remove(self.request_name)
			self.request_name = False
			return self.clock, False, False, self.devices
	
	
	def set_attr(self, c, attr, val):
	#Set the value of a given attribute
	#Generally called remotely
		self.update_clock(c)
		setattr(self, attr, val)
		logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Attribute ' + str(attr) + ' was set to: ' + str(val))
		print('Attribute ' + str(attr) + ' was set to: ' + str(val))
		if((attr == 'state') and (not(self.name == 'backend'))):
			self.db_put(self.name, val)
		if(attr == 'motion_mode'):
			displays = self.devices_by_name('display')
			for i in displays:
				try:
					r = iot.build_receiver(i)
					c = r.display_message(self.clock, 'Motion mode was set to: ' + str(val))
					self.update_clock(c)
				except:
					logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Could not connect to the display device at ' + str(compose_address(i['ip'], i['port'])))
					print('WARNING: Could not connect to the display device at ' + str(compose_address(i['ip'], i['port'])))
		return self.clock


	def cache_put(self, k, v):
		try:
			self.cache.pop(k)
		except KeyError:
			if len(self.cache) >= self.cache_capacity:
				self.cache.popitem(last=False)
			self.cache[k] = value
	
	
	def cache_get(self, k):
		try:
			v = self.cache.pop(k)
			self.cache[k] = v
			return v
		except KeyError:
			return KeyError


	def db_update(self, c, k, v):
		#Called remotely by another gateway when it writes to its database
		#Used by all other databases to make the same change without propagating a duplicate change
		self.update_clock(c)
		self.cache_put(k, v)
		try:
			backend = {'ip': self.backend_ip, 'port': self.backend_port}
			b = iot.build_receiver(backend)
			c = b.db_put(self.clock, k, v)
			self.update_clock(c)
			self.clock += 1
			return self.clock()
		except:
			if not ((self.backend_ip == False) and (self.backened_port == False)):
			#If a backend is registered but can't be reached, unregister it and submit a new request
				self.backend_ip == False
				self.backend_port == False
				self.request_db()
			self.clock += 1
			return self.clock()
	

	def db_put(self, k, v):
	#Contact the backend device to store a value in the persistent databases
	#Store a copy in the local cache first in case it's needed again soon
	#Also notify all other gateways that they should write the new value to their caches and databases
		
		self.cache_put(k, v)
		backend = {'ip': self.backend_ip, 'port': self.backend_port}
		b = iot.build_receiver(backend)
		c = b.db_put(self.clock, k, v)
		self.update_clock(c)
		
		gateways = self.devices_by_name('gateway')
		for g in gateways:
			self.clock += 1
			r = iot.build_receiver(g)
			c = r.db_update(self.clock, k, v)
			self.update_clock(c)
			
			
	def db_get_state(self, k):
	#Contact all backend devices to retrieve a list of values from the persistent state database replicas
	#Check the local cache first, then retrieve from a random database if the query misses.
		
		v = self.cache_get(k)
		if(v != KeyError):
			return [v]
			
		else:
			db = {'ip': self.backend_ip,  'port': self.backend_port}
			db = self.device_by_name('backend')
			values = []
			for db in dbs:
				self.clock += 1
				r = build_receiver(db)
				c, v = r.db_get_state(self.clock, k)
				self.update_clock(c)
				values.append(v)
			if(values == []):
				return values
			else:
				self.cache_set(k, values)
				return values
	
	def db_get_history(self, k):
	#Contact all backend devices to retrieve a list of values from the persistent history database replicas
	
		dbs = self.devices_by_name('backend')
		values = []
		for db in dbs:
			self.clock += 1
			r = build_receiver(db)
			c, v = r.db_get(self.clock, k)	
			self.update_clock(c)
			values.append(v)
		return values

	
	def handle_temperature(self):
	#Check the current temperature and adjust outlets accordingly
	
		temp_sensors = self.devices_by_name('temperature')
		outlets = self.devices_by_name('outlet')
		if(len(temp_sensors) < 1):
		#If no temperature sensors are registered, exit
			logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Temperature handling failed, no temperature sensors registered')
			#print('WARNING: Temperature handling failed, no temperature sensors registered')
		elif(len(outlets) < 1):
		#If no outlets are registered, exit
			logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Temperature handling failed, no outlets registered')
			#print('WARNING: Temperature handling failed, no outlets registered')
		else:
			temperatures = []
			for t in temp_sensors:
			#Get the state of each registered temperature sensor
				try:
					self.clock += 1
					r = iot.build_receiver(t)
					c, val = r.get_attr(self.clock, 'state')
					self.update_clock(c)
					if((type(val) == int) or (type(val) == float)):
						temperatures.append(val)
				except:
					logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to contact temperature sensor: ' + str(t))
					print('WARNING: Failed to contact temperature sensor: ' + str(t))
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Read temperature value(s) of: ' + str(temperatures))
			if (len(temperatures) == 0):
			#If no registered temperature sensors could be contacted, exit
				logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Temperature handling failed, could not contact any temperature sensors')
				print('WARNING: Temperature handling failed, could not contact any temperature sensors')
			else:
			#Calculate the average of all reported temperature values, and turn on or off all registered outlets accordingly
			#For T < 1, turn them on.  For T > 2, turn them off.
				temperature = sum(temperatures) / len(temperatures)
				if(temperature < 1):
					logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Temperature is below 1 degree, turning outlets on')
					for o in outlets:
						try:
							self.clock += 1
							r = iot.build_receiver(o)
							c = r.set_attr(self.clock, 'state', 1)
							self.update_clock(c)
							logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Turned outlet on: ' + str(o))
						except:
							logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to contact outlet: ' + str(o))
							print('WARNING: Failed to contact outlet: ' + str(o))
				elif(temperature > 2):
					logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Temperature is above 2 degrees, turning outlets off')
					for o in outlets:
						try:
							self.clock += 1
							r = iot.build_receiver(o)
							c = r.set_attr(self.clock, 'state', 0)
							self.update_clock(c)
							logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Turned outlet off: ' + str(o))
						except:
							logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to contact outlet: ' + str(o))
							print('WARNING: Failed to contact outlet: ' + str(o))
			
							
	def monitor_temperature(self):
	#Run the handle_temperature function continuously on a regular interval
	
		while(1):
			self.clock += 1
			self.handle_temperature()
			time.sleep(self.temperature_interval)
				
									
	def alert_user(self):
	#Send an intruder alert to the user display
	
		displays = self.devices_by_name('display')
		for i in displays:
			try:
				self.clock += 1
				r = iot.build_receiver(i)
				c = r.display_message(self.clock, '!!! INTRUDER DETECTED !!!')
				self.update_clock(c)
				logging.debug('User Alerted')
				print('User Alerted')
			except:
				logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Could not connect to the display device at ' + str(compose_address(i['ip'], i['port'])))
				print('WARNING: Could not connect to the display device at ' + str(compose_address(i['ip'], i['port'])))					

	def handle_motion(self, c):
	#Triggered by the motion sensor when it detects motion
	
		self.update_clock(c)
		if self.motion_mode == 'HOME':
		#If the current mode is 'HOME', turn on the bulb
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Motion detected, turning bulbs on')
			bulbs = self.devices_by_name('bulb')
			if(len(bulbs) == 0):
				logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Motion handling failed, no bulbs registered')
				#print('WARNING: Motion handling failed, no bulbs registered')
				self.clock += 1
				time.sleep(10)
			else:
				for b in bulbs:
					try:
						self.clock += 1
						logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Turning on bulb: ' + str(b))
						r = iot.build_receiver(b)
						c = r.set_attr(self.clock, 'state', 1)
						self.update_clock(c)
						logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Turned bulb on: ' + str(b))
					except:
						logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to contact bulb: ' + str(b))
						print('WARNING: Failed to contact bulb: ' + str(b))
		else:
		#If the current mode is anything but 'HOME', send an intruder alert to the user
			print('!!! INTRUDER DETECTED !!!')
			logging.critical(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + '!!! INTRUDER DETECTED !!!')
			self.alert_user()
			
			
	'''
	#Uncomment this function to use a pull-based presence sensor instead of push-based
	def monitor_presence(self):
		sensors = self.devices_by_name('presence')
		states = []
		for i in sensors:
			try:
				self.clock += 1
				r = iot.build_receiver(i)
				c, v = r.get_attr('state')
				self.update_clock(c)
				states.append(v)
		if(1 in states):
		#If any presence sensors detect a user present, set motion mode to 'HOME'
			self.clock += 1
			self.motion_mode = 'HOME'
			self.db_put(self.clock, 'motion_mode', 'HOME')
			
		else:
		#Otherwise, set motion mode to 'AWAY'
			self.clock += 1
			self.motion_mode = 'AWAY'
			self.db_put(self.clock, 'motion_mode', 'AWAY')
	'''
	
	def handle_door_state(self, c, state):
	#Called remotely by the door sensor whenever its state changes
	#If the door is opened, update the device list, and check all presence sensors to see if a user is home
	#If no presence sensors respond positively, send an intruder alert to the user device(s)
		self.update_clock(c)
		if state == 0:
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Door was closed')
			return self.clock
		else:
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Door was opened')
			presence = self.devices_by_name('presence')
			for i in presence:
				try:
					r = iot.build_receiver(i)
					c, s = r.get_attr(self.clock)
					self.update_clock(c)
					if s == 1:
						logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'User is home, not sending alert')
						return self.clock
				except:
					logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to contact presence sensor: ' + str(i))
			self.alert_user()
			return self.clock

	def cleanup(self):
	#Called on keyboard interrupt to gracefully shut the gateway down
	#First, delete any own open request files
	#Then delete own address from gateway_list.txt
	#Finally, inform all other gateways that they should remove you from their self.devices lists
		if self.request_name:
			try:
				os.remove(self.request_name)
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Removed open db request: ' + str(self.request_name))
			except:
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to remove db request: ' + str(self.request_name))
				
		with open('gateway_list.txt', 'r') as f:
			addresses = f.readlines()
		new_addresses = []
		for i in addresses:
			i = i.strip()
			if i == self.address():
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Deleting line from gateway_list: ' + str(i))
				pass
			else:
				new_addresses.append(i)
		f = open('gateway_list.txt', 'w')
		for i in new_addresses:
			f.write(str(i) + '\n')
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Rewrote gateway_list file without own address')
		f.close()
		
		self.old_device(self.id)
	


def main():

	#Create a new gateway instance
	d = gateway()
	
if __name__ == '__main__':
	main()