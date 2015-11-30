# Samuel DeLaughter
# 4/10/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import xmlrpclib
import logging
import socket
import random
import time
import iot


class door(iot.device):
#The class defining the door sensor object
#Can be set to open (1) or closed (0), or queried for its current state
	def __init__(self):
		iot.device.__init__(self)
		self.name = 'door'
		self.category = 'device'
		self.state = 0
		self.sensing_interval = 5
	
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
		
		self.server.register_function(self.sense)
		
		self.clock += 1
		try:
			print '\nStarting Server'
			print 'Use Control-C to exit'
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Starting Server')
			self.server.serve_forever()
		except KeyboardInterrupt:
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received keyboard interrupt, stopping server')
			print 'Exiting'
			
			
	def sense(self):
	#Informs the gateway to change its door_state attribute whenever the state changes
	#If open, it has a 75% chance of closing
	#If closed, it has a 25% chance of opening
		if self.state == 1:
			p = 0.75
		else:
			p = 0.25
		if(random.random() <= p):
			s = int(not(self.state))
			self.state = s
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'State was set to ' + str(s))
			print('State was set to ' + str(s))
			self.clock += 1
			self.db_put(self.name, self.state)
				
			try:
			#Set the gateway's door_state attribute
				r = iot.gateway_connection()
				c = r.handle_door_state(self.clock, s)
				self.update_clock(c)
				logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Set gateway door state to: ' + str(s))
			except:
				logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to contact gateway')
				print('WARNING: Failed to contact gateway')
				self.register()
			
	def get_attr(self, c, attr):
	#Called remotely to get the value of a given attribute
	#If the state attribute is requested, run self.sense() to update it before returning it
	#Otherwise, act identical to iot.device.get_attr()
	
		self.update_clock(c)
		if(attr == 'state'):
			self.sense()
			logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'State was queried, returning ' + str(self.state))
			print('State was queried, returning ' + str(self.state))
			return self.clock, self.state
		elif(hasattr(self, attr)):
			v = getattr(self, attr)
			return self.clock, v
		else:
 			return self.clock, None
			
	def start_client(self):
	#Start the client to monitor for user presence
	
		while True:
			self.sense()
			time.sleep(self.sensing_interval)

def main():
	#Set up logging
	iot.setup_log('door')
	#Create a new instance of the door object
	d=door()
	#Register with the gateway
	d.register()
	
	#Initialize and start daemon thread for serving as the clock synchronization leader
	leader_thread=Thread(target=d.lead, name='Door Leader Thread')
	leader_thread.daemon = True
	leader_thread.start()
	
	#Initialize and start daemon thread for the client to push state changes to the server
	client_thread=Thread(target=d.start_client, name='Door Client Thread')
	client_thread.daemon = True
	client_thread.start()
	
	#Start the door server
	d.serve()
	
if __name__ == '__main__':
	main()
