#Samuel DeLaughter
#3/16/15

from random import random
import xmlrpclib
import logging
import socket
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
	device_type='sensor'
	device_name='motion'
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
	
def report_state():
#Inform the server that motion was detected
	server = xmlrpclib.ServerProxy(get_gateway_address())
	logging.info('Detected motion, reporting to server...')
	print('Detected Motion')
	attempts = 0
	while attempts < 5:
		try:
			response=server.motion_reported()
			logging.debug('Got response: ' + str(response))
			attempts = 6
			return
		except:
			logging.warning('REPORTING TO SERVER FAILED, Trying again...')
			print('WARNING: REPORTING TO SERVER FAILED, Trying again...')
			time.sleep(attempts)
			attempts += 1
	register()
	report_state()
	
def monitor_motion():
#Check for motion, report to server if detected
#Since there is no actual hardware sensor to get a value from, simply has a 10% chance of reporting motion
	if(random() > 0.9):
		report_state()
	
def start_client():
#Start the client to monitor for motion
	while True:
		monitor_motion()
		time.sleep(1)

def main():
	#Set up logging
	logging.basicConfig(filename='logs/motion.log', filemode='w', level=logging.DEBUG, format='%(asctime)s.%(msecs)3d | %(levelname)8s | %(funcName)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S")

	SELF_IP, SELF_PORT = register()
	
	try:
		print 'Use Control-C to exit'
		start_client()
	except KeyboardInterrupt:
		logging.info('Received Keyboard Interrupt')
		logging.info('Stopping Server')
		print 'Exiting'
		
if __name__ == '__main__':
	main()