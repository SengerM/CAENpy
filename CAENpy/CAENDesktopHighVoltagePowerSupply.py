import serial
import socket
import platform
import time

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
	def __init__(self, port=None, ip=None, default_BD0=True, timeout=1):
		# The <timeout> defines the number of seconds to wait until an error is raised if the instrument is not responding. Note that this instrument has the "not nice" behavior that some errors in the commands simply produce a silent answer, instead of reporting an error. For example, if you request the value of a parameter with a "BD" that is not in the daisy-chain, the instrument will give no answer at all, only silence. And you will have to guess what happened.
		if default_BD0 not in [True, False]:
			raise ValueError(f'The argument <default_BD0> must be either True of False. Received {default_BD0}.')
		self.default_BD0 = default_BD0
		
		if ip is not None and port is not None: # This is an error, which connection protocol should we use?
			raise ValueError(f'You have specified both <port> and <ip>. Please specify only one of them to use.')
		elif ip is not None and port is None: # Connect via Ethernet.
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.connect((ip, 1470)) # According to the user manual the port 1470 always has to be used.
			self.socket.settimeout(timeout)
		elif port is not None and ip is None: # Connect via USB serial port.
			self.serial_port = serial.Serial(
				# This configuration is specified in the user manual.
				port = port,
				baudrate = 9600,
				parity = serial.PARITY_NONE,
				stopbits = 1,
				bytesize = 8,
				xonxoff = True,
				timeout = timeout,
			)
		else: # Both <port> and <ip> are none...
			raise ValueError(f'Please specify a serial port or an IP addres in which the CAEN device can be found.')
		
	def send_command(self, CMD, PAR, CH=None, VAL=None, BD=None):
		# Send a command to the CAEN device. The parameters of this method are the ones specified in the user manual.
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
		# Reads the answer from the CAEN device.
		if hasattr(self, 'serial_port'): # This means that we are talking through the serial port.
			received_bytes = self.serial_port.readline()
		elif hasattr(self, 'socket'): # This means that we are talking through an Ethernet connection.
			received_bytes = self.socket.recv(1024)
		else:
			raise RuntimeError(f'There is no serial or Ethernet communication.')
		return received_bytes.decode('ASCII').replace('\n','').replace('\r','') # Remove the annoying '\r\n' in the end and convert into a string.
	
	def query(self, CMD, PAR, CH=None, VAL=None, BD=None):
		# Sends a command and reads the answer.
		self.send_command(BD=BD, CMD=CMD, PAR=PAR, CH=CH, VAL=VAL)
		return self.read_response()
	
	def get_single_channel_parameter(self, parameter: str, channel: int, device: int=None):
		# Gets the current value of some parameter (see "MONITOR commands related to the Channels" in the CAEN user manual.)
		# parameter: This is the <whatever> value in "PAR:whatever" that is specified in the user manual.
		# channel: Integer number specifying the numer of the channel.
		# device: If you have more than 1 device connected in the daisy chain, use this parameter to specify the device number (In the user manual this is the <whatever> that goes in "BD:whatever").
		response = self.query(CMD='MON', PAR=parameter, CH=channel, BD=device)
		if check_successful_response(response) == False:
			raise RuntimeError(f'Error trying to get the parameter {parameter}. The response from the instrument is: "{response}"')
		parameter_value = response.split('VAL:')[-1]
		if parameter_value.isdigit(): # This means it only contains numerical values, thus it is an int.
			return int(parameter_value)
		try:
			parameter_value = float(parameter_value)
		except:
			pass
		return parameter_value
	
	def set_single_channel_parameter(self, parameter: str, channel: int, value, device: int=None):
		# Sets the value of some parameter (see "SET commands related to the Channels" in the CAEN user manual.)
		# parameter: This is the <whatever> value in "PAR:whatever" that is specified in the user manual.
		# channel: Integer number specifying the numer of the channel.
		# device: If you have more than 1 device connected in the daisy chain, use this parameter to specify the device number (In the user manual this is the <whatever> that goes in "BD:whatever").
		response = self.query(CMD='SET', PAR=parameter, CH=channel, BD=device, VAL=value)
		if check_successful_response(response) == False:
			raise RuntimeError(f'Error trying to set the parameter {parameter}. The response from the instrument is: "{response}"')
	
	def ramp_voltage(self, voltage: float, channel: int, device: int = None, ramp_speed_VperSec: float = 5, timeout: float = 10):
		# Blocks the execution until the ramp is completed.
		# timeout: It is the number of seconds to wait until the VMON (measured voltage) is stable. After this number of seconds, an error will be raised because the voltage cannot stabilize.
		current_ramp_speed_settings = {}
		for i in ['up', 'down']:
			current_ramp_speed_settings[i] = self.get_single_channel_parameter(
				parameter = 'RUP' if i == 'up' else 'RDW',
				channel = channel,
				device = device,
			)
			self.set_single_channel_parameter(
				parameter = 'RUP' if i == 'up' else 'RDW',
				channel = channel,
				device = device,
				value = ramp_speed_VperSec,
			)
		try:
			current_VSET = self.get_single_channel_parameter(
				parameter = 'VSET',
				channel = channel,
				device = device,
			)
			self.set_single_channel_parameter(
				parameter = 'VSET',
				channel = channel,
				device = device,
				value = voltage,
			)
			if voltage != current_VSET:
				time.sleep(((voltage-current_VSET)**2)**.5/ramp_speed_VperSec)
				previous_VMON = self.get_single_channel_parameter(
					parameter = 'VMON',
					channel = channel,
					device = device,
				)
				n_waited_seconds = 0
				while True: # Here I wait until it stabilizes. In my experience it requires a few extra seconds, but the amount of seconds is a function of DeltaV, the ramp speed, etc.
					time.sleep(1)
					n_waited_seconds += 1
					current_VMON = self.get_single_channel_parameter(
						parameter = 'VMON',
						channel = channel,
						device = device,
					)
					if int(current_VMON*10) == int(previous_VMON*10):
						break
					previous_VMON = current_VMON
					if n_waited_seconds > timeout: # If this happens, better to raise an error that I cannot set the voltage. Otherwise this can be blocked forever.
						raise RuntimeError(f'Cannot reach a stable voltage after a timeout of {timeout} seconds.')
		except Exception as e:
			raise e
		finally:
			for i in ['up', 'down']:
				self.set_single_channel_parameter(
					parameter = 'RUP' if i == 'up' else 'RDW',
					channel = channel,
					device = device,
					value = current_ramp_speed_settings[i],
				)
	
