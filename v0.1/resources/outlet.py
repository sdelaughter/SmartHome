from SimpleXMLRPCServer import SimpleXMLRPCServer
import xmlrpclib
import logging
import socket
import time

STATE = 0

def get_gateway_address():
#Read the gateway's address from the gateway_ip.txt file
	ip_file=open('gateway_ip.txt', 'r')
	with open('gateway_ip.txt', 'r') as f:
		address = ('http://' + str(f.readlines()[0]))
	logging.info('Read gateway address from file: ' + str(address))
	return(address)

def register():
#Register with the gateway
	device_type='device'
	device_name='outlet'
	ip = socket.gethostbyname(socket.gethostname())
	logging.info('Detected self IP address of: ' + str(ip))
	registered = False
	while not registered:
		logging.info('Attempting to register with the gateway')
		print('Attempting to register with the gateway')
		try:
			proxy = xmlrpclib.ServerProxy(get_gateway_address(), allow_none=True)
			port = proxy.register(device_type, device_name, ip)
			logging.info('Registered with gateway and received Device ID: ' + str(port))
			print('Registered with gateway and received Device ID: ' + str(port))
			logging.info('Using port number: ' + str(port))
			print('Using port number: ' + str(port))
			registered = True
			return ip, port
		except:
			logging.warning('Failed to register with the gateway, trying again in 10 seconds')
			print('Failed to register with the gateway, trying again in 10 seconds')
			time.sleep(10)
				
def get_state():
#Query the current state of the bulb
	global STATE
	logging.debug('State was queried, returning: ' + str(STATE))
	return STATE

	
def set_state(s):
#Change the state of the bulb
	global STATE
	STATE = s
	logging.debug('State was changed to: ' + str(s))
	print('State was changed to: ' + str(s))
	return

def start_server(server):
#Listen for requests from the gateway
	try:
		print('Use Control-C to exit')
		logging.info('Starting Server')
		
		server.serve_forever()
	except KeyboardInterrupt:
		logging.info('Received Keyboard Interrupt')
		logging.info('Stopping Server')
		print('Exiting')
		
def main():
	#Set up logging
	logging.basicConfig(filename='logs/outlet.log', filemode='w', level=logging.DEBUG, format='%(asctime)s.%(msecs)3d | %(levelname)8s | %(funcName)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S")

	SELF_IP, SELF_PORT = register()
	server = SimpleXMLRPCServer((SELF_IP, SELF_PORT), logRequests=False, allow_none=True)
	server.register_function(get_state)
	server.register_function(set_state)
	server.register_function(register)
	start_server(server)
	
if __name__ == '__main__':
	main()