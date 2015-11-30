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

class display(iot.device):
#The class defining the user display object
	def __init__(self):
		iot.device.__init__(self)
		self.name = 'display'
		self.category = 'display'
		
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
		
		self.server.register_function(self.display_message)
		
		self.clock += 1
		try:
			print '\nStarting Server'
			print 'Use Control-C to exit'
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Starting Server')
			self.server.serve_forever()
		except KeyboardInterrupt:
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received keyboard interrupt, stopping server')
			print 'Exiting'
		
	def display_message(self, c, message):
	#Triggered by other devices to print a message to the user display
		self.update_clock(c)
		logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Displaying received message: ' + str(message))
		print message
		return self.clock
				
def main():
	#Set up logging
	iot.setup_log('display')
	#Create a new instance of the user object
	d=display()
	#Register with the gateway
	d.register()
	
	#Initialize and start daemon thread for serving as the clock synchronization leader
	leader_thread=Thread(target=d.lead, name='Display Leader Thread')
	leader_thread.daemon = True
	leader_thread.start()
	
	#Start the display server
	d.serve()
	
if __name__ == '__main__':
	main()
