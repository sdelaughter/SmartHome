# Samuel DeLaughter
# 4/10/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import xmlrpclib
import logging
import random
import time
import iot

class motion(iot.device):
#The class defining motion sensor devices
	def __init__(self):
		iot.device.__init__(self)
		self.name = 'motion'
		self.category = 'sensor'
		self.sensing_interval = 5
		
	def sense(self):
	#Has a 1/4 chance of changing the motion sensor's current state
	#Then informs the gateway of motion if the current state is 1
		if(random.random() > 0.75):
			self.state = int(not(self.state))
			self.clock += 1
			self.db_put(self.name, self.state)
		if self.state == 1:
			try:
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Detected motion, reporting to gateway...')
				r = iot.gateway_connection()
				c = r.handle_motion(self.clock)
				self.update_clock(c)
				logging.debug(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Reported motion to gateway')
				print('Detected motion and reported to gateway')
			except:
				logging.warning(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Failed to report motion to gateway')
				print('WARNING: Failed to report motion to gateway')
				self.register()
		else:
			self.state = 0
			
	def start_client(self):
	#Start the client to monitor for motion
		while True:
			self.sense()
			time.sleep(self.sensing_interval)

def main():
	
	#Set up logging
	iot.setup_log('motion')	
	#Create a new instance of the motion sensor object
	d = motion()
	#Register with the gateway
	d.register()
	
	#Initialize and start daemon thread for serving as the clock synchronization leader
	leader_thread=Thread(target=d.lead, name='Motion Leader Thread')
	leader_thread.daemon = True
	leader_thread.start()
	
	#Start the motion sensing client
	d.start_client()
	
		
if __name__ == '__main__':
	main()
