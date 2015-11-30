# Samuel DeLaughter
# 4/10/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import logging
import iot
		
class outlet(iot.device):
#The class defining outlet devices
#Can be turned on or off, or queried for the current state

	def __init__(self):
		iot.device.__init__(self)
		self.name = 'outlet'
		self.category = 'device'

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

def main():
	
	#Set up logging
	iot.setup_log('outlet')
	#Create a new instance of the outlet object
	d = outlet()
	#Register with the gateway
	d.register()
	
	#Initialize and start daemon thread for serving as the clock synchronization leader
	leader_thread=Thread(target=d.lead, name='Outlet Leader Thread')
	leader_thread.daemon = True
	leader_thread.start()
	
	#Start the outlet server
	d.serve()
	
if __name__ == '__main__':
	main()
