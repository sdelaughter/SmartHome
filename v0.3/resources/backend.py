# Samuel DeLaughter
# 5/8/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import socket
import time
import os

import logging
import shelve


import iot


class backend(iot.device):
#The class defining backend devices, which manage persistent database storage
#Uses two separate database files, one for current device states, and another for the full history of past and present states
#Uses python's native shelve module to read and write the database files
#
#Note that shelve files are not human readable
#The following example illustrates how to manually retrieve a value from key 'bulb' in the state database
#
#>>> import shelve
#>>> d = shelve.open('state_db')
#>>> value = d['bulb']
#>>> d.close()
#>>> return value

	def __init__(self):
		iot.device.__init__(self)
		self.name = 'backend'
		self.category = 'backend'
		
		'''
		#Initialize and start daemon thread for serving as the clock synchronization leader
		leader_thread=Thread(target=self.lead, name='Bulb Leader Thread')
		leader_thread.daemon = True
		leader_thread.start()
		'''
		
		#Set up logging and create the database files
		self.setup()
		
		#Find an open request file from a gateway and contact it to register
		self.register()
		
		#Initialize and start daemon thread for checking to see if the gateway is still up
		gateway_heartbeat=Thread(target=self.gateway_heartbeat, name='Gateway Heartbeat Thread')
		gateway_heartbeat.daemon = True
		gateway_heartbeat.start()
		
		#Start listening for requests
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
		self.server.register_function(self.db_get_state)
		self.server.register_function(self.db_get_history)
		#self.server.register_function(self.set_leader)
		self.server.register_function(self.device_by_name)
		self.server.register_function(self.devices_by_name)
		self.server.register_function(self.update_device_list)
		
		self.server.register_function(self.db_put)
		self.server.register_function(self.db_get_state)
		self.server.register_function(self.db_get_history)
		
		self.clock += 1
		try:
			print '\nStarting Server'
			print 'Use Control-C to exit'
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Starting Server')
			self.server.serve_forever()
		except KeyboardInterrupt:
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received keyboard interrupt, stopping server')
			print 'Exiting'
	
	
	def setup(self):
		#Set up logging and initialize database files
		t = time.localtime()
		iot.setup_log(self.name, time.localtime())
		logging.info('Initializing')
		timestamp = (str(t[0]) + '_' + str(t[1]) + '-' + str(t[2]) + '_' + str(t[3]) + '-' + str(t[4]) + '-' + str(t[5]))
		self.history_file = ('db/' + str(timestamp) + '_history')
		h=shelve.open(self.history_file)
		h.close()
		self.state_file = ('db/' + str(timestamp) + '_state')
		s=shelve.open(self.state_file)
		s.close()
		
		
	def register(self):
		registered = False
		while not registered:
			requests = os.listdir('db_requests/')
			valid_requests = []
			for i in requests:
				if not i.startswith('req_'):
					logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Ignoring improperly named request file: ' + str(i))
				else:
					valid_requests.append(i)
			if(len(valid_requests) == 0):
			#If there are no open gateway requests, wait five seconds and check again
				time.sleep(5)
				continue
			request = min(valid_requests)
			print('Attempting to answer request: ' + str(request))
			filename = ('db_requests/' + str(request))
			f = open(filename, 'r')
			address = f.readlines()
			ip = address[0].strip()
			port = int(address[1].strip())
			print('Found request address of: ' + str(iot.compose_address(ip, port)))
			gateway = {'ip': ip, 'port': port}
			
			try:
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Attempting to register with gateway at: ' + str(iot.compose_address(ip, port)))
				g = iot.build_receiver(gateway)
				self.ip = socket.gethostbyname(socket.gethostname())
				self.clock += 1
				c, id, port, devices = g.register_db(self.clock, self.name, self.ip)
				self.update_clock(c)
				if((id == False) or (port == False)):
					continue
				else:
					print('Registered with gateway. Received:\n\tID: ' + str(id) + '\n\tPort: ' + str(port))
					logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Registered with gateway. Using port number: ' + str(port))
					self.id = id
					self.port = port
					self.devices = devices
					self.gateway_ip = gateway['ip']
					print self.gateway_ip
					self.gateway_port = gateway['port']
					print self.gateway_port
					registered = True
					print registered
					break
			except:
				logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to register with the gateway, trying another request')
				time.sleep(5)
				continue
	
	
	def gateway_heartbeat(self):
		while 1:
			if((self.gateway_ip == False) or (self.gateway_port == False)):
				print('gateway_ip: ' + str(self.gateway_ip))
				print('gateway_port: ' + str(self.gateway_port))
				print 'Reregistering!'
				self.register()
			else:
				g = {'ip': self.gateway_ip, 'port': self.gateway_port}
				g = iot.build_receiver(g)
				try:
					c = g.ping(self.clock)
					self.update_clock(c)
					logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Gateway still alive, checking again in 5 seconds')
					time.sleep(5)
				except:
					logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Gateway unreachable, checking for a new registration request')

					self.gateway_ip = False
					self.gateway_port = False
					continue
		
		
	def db_put(self, c, k, v):
	#Store something in the persistent databases
	
		self.update_clock(c)

		#Store a 3-tuple of (key, value, timestamp) in the history file with the current logical clock value as the key 
		h = shelve.open(self.history_file)
		key = self.clock
		h[str(key)] = (k, v, self.timestamp())
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Put history item at key ' + str(key))
		h.close()
		self.clock += 1
		
		#Store a 3-tuple of (value, logical_clock_value, timestamp) in the state file under the given key
		s = shelve.open(self.state_file)
		s[str(k)] = (v, self.clock, self.timestamp())
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Put state item at key ' + str(k))
		s.close()
		self.clock += 1
		
		return self.clock
			
	def db_get_history(self, c, k):
	#Retrieve an entry from the persistent history database
	#Returns the value as a 3-tuple of (key, value, timestamp) where the key is the name of the deivce related to the state value
	
		self.update_clock(c)
		f = shelve.open(self.history_file)
		v = f[str(k)]
		f.close()
		self.clock += 1
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Returning history item at key ' + str(k))
		return(self.clock, v)		
	
	def db_get_state(self, c, k):
	#Retrieve an entry from the persistent state database
	#Returns the value as a 3-tuple of (key, value, timestamp) where the key is the name of the deivce related to the state value
	
		self.update_clock(c)
		f = shelve.open(self.state_file)
		v = f[str(k)]
		f.close()
		self.clock += 1
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Returning state item at key ' + str(k))
		return(self.clock, v)


def main():
	#Create a new instance of the backend object
	d=backend()

	
if __name__ == '__main__':
	main()