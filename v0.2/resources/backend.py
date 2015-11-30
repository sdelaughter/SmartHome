# Samuel DeLaughter
# 4/10/15


from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread
import logging
import shelve
import socket
import time
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
		
		t = time.localtime()
		timestamp = (str(t[0]) + '_' + str(t[1]) + '-' + str(t[2]) + '_' + str(t[3]) + '-' + str(t[4]) + '-' + str(t[5]))
		self.history_file = ('db/' + str(timestamp) + '_history')
		self.state_file = ('db/' + str(timestamp) + '_state')
		
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
	
	#Set up logging
	iot.setup_log('backend')
	#Create a new instance of the backend object
	d=backend()
	#Register with the gateway
	d.register()
	
	#Initialize and start daemon thread for serving as the clock synchronization leader
	leader_thread=Thread(target=d.lead, name='Backend Leader Thread')
	leader_thread.daemon = True
	leader_thread.start()
	
	#Start the backend server
	d.serve()
	
if __name__ == '__main__':
	main()
