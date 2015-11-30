# Samuel DeLaughter
# 5/8/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import logging
import random
import time
import iot

class temp(iot.device):
#The class defining temperature sensor devices

	def __init__(self):
		iot.device.__init__(self)
		self.name = 'temperature'
		self.category = 'sensor'
		
		#Set up logging
		iot.setup_log(self.name, time.localtime())
		
		#Register with the gateway
		self.register()
		
		'''
		#Initialize and start daemon thread for serving as the clock synchronization leader
		leader_thread=Thread(target=self.lead, name='Temperature Leader Thread')
		leader_thread.daemon = True
		leader_thread.start()
		'''
		
		#Start the server
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
	#"Sense" the current temperature
	#Pick a random integer from -20 to 40 and set it as self.state
	
		s = random.randint(-20, 40)
		self.state = s
		self.clock += 1
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Sensed state: ' + str(s))
		
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

def main():
	#Create a new instance of the temperature sensor object
	d = temp()
	
	
if __name__ == '__main__':
	main()