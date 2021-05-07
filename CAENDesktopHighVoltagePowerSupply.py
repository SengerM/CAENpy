import serial
import socket
import platform

def create_command_string(BD, CMD, PAR, CH=None, VAL=None):
	try:
		BD = int(BD)
	except:
		raise ValueError(f'<BD> must be an integer number. Received {BD} of type {type(BD)}.')
	if not 0 <= BD <= 31:
		raise ValueError(f'<BD> must be one of {{0,1,...,31}}, received {BD}.')
	command = f'$BD:{BD},CMD:{CMD},'
	if CH is not None:
		try:
			CH = int(CH)
		except:
			raise ValueError(f'<CH> must be an integer number, received {CH} of type {type(CH)}.')
		if not 0 <= CH <= 8:
			raise ValueError(f'<CH> must be one of {{0,1,...,8}}, received {CH}.')
		command += f'CH:{CH},'
	command += f'PAR:{PAR},'
	if VAL is not None:
		command += f'VAL:{VAL},'
	command = command[:-1] # Remove the last ','
	command += '\r\n'
	return command

def check_successful_response(response_string):
	if not isinstance(response_string, str):
		raise TypeError(f'<response_string> must be an instance of <str>, received {response_string} of type {type(response_string)}.')
	return 'OK' in response_string # According to the user manual, if there was no error the answer always contains an "OK".

class CAENDesktopHighVoltagePowerSupply:
	# This class was implemented according to the specifications in the 
	# user manual here: https://www.caen.it/products/dt1470et/
	def __init__(self, port=None, ip=None, default_BD0=True):
		if default_BD0 not in [True, False]:
			raise ValueError(f'The argument <default_BD0> must be either True of False. Received {default_BD0}.')
		self.default_BD0 = default_BD0
		
		if ip is not None and port is not None: # This is an error, which connection protocol should we use?
			raise ValueError(f'You have specified both <port> and <ip>. Please specify only one of them to use.')
		elif ip is not None and port is None: # Connect via Ethernet.
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.connect((ip, 1470)) # According to the user manual the port 1470 always has to be used.
		elif port is not None and ip is None: # Connect via USB serial port.
			self.serial_port = serial.Serial(
				# This configuration is specified in the user manual.
				port = port,
				baudrate = 9600,
				parity = serial.PARITY_NONE,
				stopbits = 1,
				bytesize = 8,
				xonxoff = True,
				timeout = 9,
			)
		else: # Both <port> and <ip> are none...
			raise ValueError(f'Please specify a serial port or an IP addres in which the CAEN device can be found.')
	
	def send_command(self, CMD, PAR, CH=None, VAL=None, BD=None):
		if BD is None:
			if self.default_BD0 == True:
				BD = 0
			else:
				raise ValueError(f'Please specify a value for the <BD> parameter. Refer to the CAEN user manual.')
		bytes2send = create_command_string(BD=BD, CMD=CMD, PAR=PAR, CH=CH, VAL=VAL).encode('ASCII')
		if hasattr(self, 'serial_port'): # This means that we are talking through the serial port.
			self.serial_port.write(bytes2send)
		elif hasattr(self, 'socket'): # This means that we are talking through an Ethernet connection.
			self.socket.sendall(bytes2send)
		else:
			raise RuntimeError(f'There is no serial or Ethernet communication.')
	
	def read_response(self):
		if hasattr(self, 'serial_port'): # This means that we are talking through the serial port.
			received_bytes = self.serial_port.readline()
		elif hasattr(self, 'socket'): # This means that we are talking through an Ethernet connection.
			received_bytes = self.socket.recv(1024)
		else:
			raise RuntimeError(f'There is no serial or Ethernet communication.')
		return received_bytes.decode('ASCII')[:-2] # Remove the annoying '\r\n' in the end and convert into a string.
	
	def query(self, CMD, PAR, CH=None, VAL=None, BD=None):
		self.send_command(BD=BD, CMD=CMD, PAR=PAR, CH=CH, VAL=VAL)
		return self.read_response()
	
	def get_single_channel_parameter(self, parameter: str, channel: int, device: int=None):
		response = self.query(CMD='MON', PAR=parameter, CH=channel, BD=device)
		if check_successful_response(response) == False:
			raise RuntimeError(f'Error trying to get the parameter {parameter}. The response from the instrument is: {response}')
		parameter_value = response.split('VAL:')[-1]
		if parameter_value.isdigit(): # This means it only contains numerical values, thus it is an int.
			return int(parameter_value)
		try:
			parameter_value = float(parameter_value)
		except:
			pass
		return parameter_value
	
	def set_single_channel_parameter(self, parameter: str, channel: int, value, device: int=None):
		response = self.query(CMD='SET', PAR=parameter, CH=channel, BD=device, VAL=value)
		if check_successful_response(response) == False:
			raise RuntimeError(f'Error trying to set the parameter {parameter}. The response from the instrument is: {response}')

if __name__ == '__main__':
	print('Via Ethernet...')
	source = CAENDesktopHighVoltagePowerSupply(ip='130.60.165.228')
	for parameter in ['IMON', 'VMON','MAXV','RUP','POL','STAT','VSET','PDWN']:
		print(f'{parameter} → {source.get_single_channel_parameter(parameter, 0)}')
	
	# ~ for parameter in ['VSET','ISET','MAXV','IMRANGE']:
		# ~ source.set_single_channel_parameter(parameter, 0, 1)
	
	print('Via USB...')
	source = CAENDesktopHighVoltagePowerSupply(port='/dev/ttyACM0')
	for parameter in ['IMON', 'VMON','MAXV','RUP','POL','STAT','VSET','PDWN']:
		print(f'{parameter} → {source.get_single_channel_parameter(parameter, 0)}')
	
	# ~ for parameter in ['VSET','ISET','MAXV','IMRANGE']:
		# ~ source.set_single_channel_parameter(parameter, 0, 1)
	
