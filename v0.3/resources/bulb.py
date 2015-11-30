# Samuel DeLaughter
# 5/8/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import logging
import time
import iot

class bulb(iot.device):
	def __init__(self):
		iot.device.__init__(self)
		self.name = 'bulb'
		self.state = 0
		self.category = 'device'
		self.last_on = time.time()
		self.shutoff_interval = 300
		
		#Set up logging
		iot.setup_log(self.name, time.localtime())
		#Register with the gateway
		self.register()
		
		'''
		#Initialize and start daemon thread for serving as the clock synchronization leader
		leader_thread=Thread(target=self.lead, name='Bulb Leader Thread')
		leader_thread.daemon = True
		leader_thread.start()
		'''
		
		#Initialize and start daemon thread to auotmatically shut off the bulb after a certain time interval
		shutoff_thread=Thread(target=self.auto_shutoff, name='Bulb Auto-Shutoff Thread')
		shutoff_thread.daemon=True
		shutoff_thread.start()
		
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
		
		self.server.register_function(self.auto_shutoff)
		
		self.clock += 1
		try:
			print '\nStarting Server'
			print 'Use Control-C to exit'
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Starting Server')
			self.server.serve_forever()
		except KeyboardInterrupt:
			logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Received keyboard interrupt, stopping server')
			print 'Exiting'
		
	def auto_shutoff(self):
		while 1:
			if self.state == 1:
				duration = time.time() - self.last_on
				if(duration >= self.shutoff_interval):
					logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Bulb has been on for ' + str(duration) + ' seconds - shutting off now')
					print('Bulb has been on for ' + str(duration) + ' seconds - shutting off now')
					self.state = 0
					self.clock += 1
				else:
					time.sleep(self.shutoff_interval - duration)
			else:
				time.sleep(self.shutoff_interval)
			
	def set_attr(self, c, attr, val):	
		self.update_clock(c)
		if(attr == 'state'):
			self.state = val
			self.clock += 1
			self.last_on = time.time()
			self.clock += 1
			self.db_put(self.name, val)
			self.clock += 1
		else:
			setattr(self, attr, val)
			self.clock += 1
		logging.info(str(self.clock) + ' | ' + str(self.timestamp()) + ': ' + 'Attribute ' + str(attr) + ' was set to: ' + str(val))
		print('Attribute ' + str(attr) + ' was set to: ' + str(val))
		return self.clock
		

def main():
	#Create a new instance of the bulb object
	d = bulb()
	
	
if __name__ == '__main__':
	main()