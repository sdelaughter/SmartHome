# Samuel DeLaughter
# 4/10/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import logging
import socket
import time
import iot

class gateway(iot.device):
#The class defining gateway devices

	def __init__(self):
		iot.device.__init__(self)
		self.id = 0
		self.ip = socket.gethostbyname(socket.gethostname())
		self.port = 9000
		self.name = 'gateway'
		#self.clock = {0: 0}
		self.devices = {'0': {'name': 'gateway', 'category': 'gateway', 'ip': self.ip, 'port': 9000}}
		self.door_state = 0
		self.motion_mode = 'HOME'
		self.temperature_interval = 10
		
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
		
		self.server.register_function(self.register_device)
		self.server.register_function(self.handle_temperature)
		self.server.register_function(self.monitor_temperature)
		self.server.register_function(self.alert_user)
		self.server.register_function(self.handle_motion)
		self.server.register_function(self.handle_door_state)
		#self.server.register_function(self.monitor_presence)
		
		self.clock += 1
		try:
			print '\nStarting Server'
			print 'Use Control-C to exit'
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Starting Server')
			self.server.serve_forever()
		except KeyboardInterrupt:
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received keyboard interrupt, stopping server')
			print 'Exiting'
		
	def register(self):
	#A replacement for the register() function defined in iot.py
	#A gateway device will never need to register, so that function should never be called by a gateway
	#Simply prints + logs a warning and returns 0
	
		logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Unable to register gateway with itself')
		print('WARNING: Unable to register gateway with itself')
		return(0)
	
	def register_device(self, c, name, ip):
	#Allow a device to register itself with the gateway
	#Called remotely by devices when they start up or are unable to contact a previously registered gateway
	#Adds a new entry to the gateway's self.devices dictionary with the device's name, category, id, ip, and port number
	#Assigns the device a port number and instructs it which port to listen on
	#Devices with different IPs may share port numbers, but every device's port number will always be greater than the gateway port
	
		self.update_clock(c)
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received registration request from ' + str(name) + ' device at ' + str(ip))
		
		#Find the next available ID number
		ids = [self.id]
		for i in self.devices:
			ids.append(int(i))
		id = str(max(ids) + 1)
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Assigning new ' + str(name) + ' device id: ' + str(id))
		
		#Find the next available port number for the device's IP
		ports = []
		for i in self.devices:
			if self.devices[i]['ip'] == ip:
				ports.append(self.devices[i]['port'])
		if(len(ports) == 0):
			port = self.port + 1
		else:
			port = (max(ports) + 1)
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Assigning new ' + str(name) + ' device port number: ' + str(port))
		
		#Register the device's info in self.devices and return an id and port number
		self.devices[id] = {'id': id, 'name': name, 'ip': ip, 'port': port}
		self.clock += 1
		print('Registered new device: ' + str(self.devices[id]))
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Registered new device: ' + str(self.devices[id]))
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Current Device List: ' + str(self.devices))
		return self.clock, id, port
	
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

def main():
	#Set up logging
	iot.setup_log('gateway')
	#Create a new instance of the gateway object
	d = gateway()
	
	#Write address to gateway_ip file
	ip_file=open('gateway_ip.txt', 'w')
	ip_file.write('http://' + str(d.ip) + ':' + str(d.port))
	ip_file.close()
	
	#Initialize and start daemon thread for serving as the clock synchronization leader
	leader_thread=Thread(target=d.lead, name='Gateway Leader Thread')
	leader_thread.daemon = True
	leader_thread.start()

	#Initialize and start daemon threads for checking temperature and automatically shutting off the bulb
	temp_thread=Thread(target=d.monitor_temperature, name='Gateway Temperature Thread')
	temp_thread.daemon = True
	temp_thread.start()
	
	#Start the main server
	d.serve()
	
if __name__ == '__main__':
	main()
