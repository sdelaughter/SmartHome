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

class user(iot.device):
#The class defining the user terminal
	def __init__(self):
		iot.device.__init__(self)
		self.name = 'user'
		self.category = 'user'
		
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
				
	def get_mode(self):
	#Return the current motion-detection mode
		try:
			r = iot.gateway_connection()
			c, mode = r.get_attr(self.clock, 'motion_mode')
			self.update_clock(c)
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Queried motion mode and received: ' + str(mode))
			return mode
		except:
			logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to contact gateway')
			print('WARNING: Failed to contact gateway')
			self.register()
		
	def set_mode(self, mode):
	#Change the motion-detection mode
		try:
			r = iot.gateway_connection()
			c = r.set_attr(self.clock, 'motion_mode', mode)
			self.update_clock(c)
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Set motion mode to: ' + str(mode)) 
		except:
			logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to contact gateway')
			print('WARNING: Failed to contact gateway')
			self.register()
	
	def usage(self):
	#Show the available user commands
		logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Printing Usage')
		print('\nAvailable Commands:\n')
		print('    HELP: Show this list again')
		print('    AWAY: Set the motion-detection mode to AWAY')
		print('    HOME: Set the motion-detection mode to HOME')
	
	def handle_input(self, input):
	#Handle user input
		logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'User entered command: ' + str(input))
		if(input == 'HOME'):
			self.set_mode('HOME')
		elif(input == 'AWAY'):
			self.set_mode('AWAY')
		else:
			if(not(input == 'HELP')):
				print('Invalid Command: ' + str(input))
			self.usage()
	
	def start_client(self):
	#Prompt for and handle user input
		self.usage()
		print('\nCurrent motion-detection mode: ' + str(self.get_mode()))
		while True:
			input = raw_input('>>> ')
			self.handle_input(input)
			self.clock += 1
		
def main():
	#Set up logging
	iot.setup_log('user')
	#Create a new instance of the user object
	d=user()
	#Register with the gateway
	d.register()
	
	#Start the client thread to handle user input
	client_thread=Thread(target=d.start_client(), name='User Client Thread')
	client_thread.daemon = True
	client_thread.start()
	
	#Initialize and start daemon thread for serving as the clock synchronization leader
	leader_thread=Thread(target=d.lead, name='User Leader Thread')
	leader_thread.daemon = True
	leader_thread.start()
	
	#Start the user server
	d.serve()
	
if __name__ == '__main__':
	main()
