#Samuel DeLaughter
#3/16/15

from SimpleXMLRPCServer import SimpleXMLRPCServer
import xmlrpclib
import logging
import thread
import socket
import random
import time


def get_gateway_address():
#Read the gateway's address from the gateway_ip.txt file
	ip_file=open('gateway_ip.txt', 'r')
	with open('gateway_ip.txt', 'r') as f:
		address = ('http://' + str(f.readlines()[0]))
	logging.info('Read gateway address from file: ' + str(address))
	return(address)

def register():
#Register with the gateway
	device_type='user'
	device_name='terminal'
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
			mode = get_mode()
			return ip, port, mode
		except:
			logging.warning('Failed to register with the gateway, trying again in 10 seconds')
			print('Failed to register with the gateway, trying again in 10 seconds')
			time.sleep(10)

def get_mode():
#Return the current motion-detection mode
	server = xmlrpclib.ServerProxy(get_gateway_address(), allow_none=True)
	try:
		return server.current_mode()
	except:
		logging.warning('FAILED TO CONTACT SERVER')
		print('WARNING: FAILED TO CONTACT SERVER')
		register()

def set_mode(mode):
#Change the motion-detection mode
	server = xmlrpclib.ServerProxy(get_gateway_address(), allow_none=True)
	try:
		response=server.change_mode(mode)
		logging.debug('Got response: ' + str(response))
		if response == 'Done':
			print('Changed motion-mode to ' + str(mode))
		else:
			print('Got anomolous response: ' + str(response))
	except:
		logging.warning('FAILED TO CONTACT SERVER')
		print('WARNING: FAILED TO CONTACT SERVER')
		register()

def print_usage():
#Show the available user commands
	logging.debug('Printing Usage')
	print('\nAvailable Commands:\n')
	print('    HELP: Show this list again')
	print('    AWAY: Set the motion-detection mode to AWAY')
	print('    HOME: Set the motion-detection mode to HOME')

def handle_input(input):
#Handle user input
	print input
	logging.debug('User entered command: ' + str(input))
	if input == 'HOME':
		set_mode('HOME')
	elif input == 'AWAY':
		set_mode('AWAY')
	else:
		if not (input == 'HELP'):
			print('Invalid Command: ' + str(input))
		print_usage()


def start_client():
#Prompt for and handle user input
	print_usage()
	print('\nCurrent motion-detection mode: ' + str(get_mode()))
	while True:
		input = raw_input('>>> ')
		handle_input(input)
		
def main():
	#Set up logging
	logging.basicConfig(filename='logs/user_terminal.log', filemode='w', level=logging.DEBUG, format='%(asctime)s.%(msecs)3d | %(levelname)8s | %(funcName)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
	
	SELF_IP, SELF_PORT, mode = register()
	start_client()
	
if __name__ == '__main__':
	main()