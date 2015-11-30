# Samuel DeLaughter
# 5/8/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import xmlrpclib
import threading
import logging
import random
import socket
import time
import iot

class presence(iot.device):
#The class defining the presence sensor object
	def __init__(self):
		iot.device.__init__(self)
		self.name = 'presence'
		self.category = 'sensor'
		self.state = 0
		self.sensing_interval = 5
		
		#Create the log file and set up its format
		iot.setup_log(self.name, time.localtime())
		
		#Register with the gateway
		self.register()
		
		'''
		#Initialize and start daemon thread for serving as the clock synchronization leader
		leader_thread=Thread(target=self.lead, name='Presence Leader Thread')
		leader_thread.daemon = True
		leader_thread.start()
		'''
		
		#Start the presence server
		self.start_client()
				
	
		
	def sense(self):
	#Has a 1/4 chance of changing the presence sensor's current state
	#Informs the gateway to change its motion_mode attribute whenever the state changes
	
		if(random.random() > 0.75):
			s = int(not(self.state))
			self.state = s
			self.clock += 1
			self.db_put(self.name, self.state)
			
			if(s == 0):
				mode = 'HOME'
			else:
				mode = 'AWAY'
				
			try:
				#Set the gateway's motion_mode attribute
				r = iot.gateway_connection()
				c = r.set_attr(self.clock, 'motion_mode', mode)
				self.update_clock(c)
				logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Set motion mode to: ' + str(mode))
				print('Set motion mode to: ' + str(mode))
			except:
				logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to contact gateway')
				print('WARNING: Failed to contact gateway')
				self.register()
				
	'''
	#Dumb version of the sense function
	#Has a 50-50 chance of setting the state to either 0 or 1
	def sense(self):
		if(random.random() > 0.5):
			self.state = 1
		else:
			self.state = 0
		self.clock += 1
	'''
				
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
	#Create a new instance of the presence sensor device object
	d=presence()

	
if __name__ == '__main__':
	main()