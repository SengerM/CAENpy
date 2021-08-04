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

def _validate_type(variable, variable_name, variable_type):
	if not isinstance(variable, variable_type):
		raise TypeError(f'<{variable_name}> expected object of type {variable_type}, received object of type {type(variable)}.')

def _validate_numeric_type(variable, variable_name, variable_numeric_type):
	try:
		variable = variable_numeric_type(variable)
	except:
		raise TypeError(f'<{variable_name}> expected object of type {variable_numeric_type}, received object of type {type(variable)}.')
	return variable

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
		ramp_speed_VperSec = _validate_numeric_type(ramp_speed_VperSec, 'ramp_speed_VperSec', float)
		voltage = _validate_numeric_type(voltage, 'voltage', float)
		timeout = _validate_numeric_type(timeout, 'timeout', float)
		channel = _validate_numeric_type(channel, 'channel', int)
		if device is not None:
			device = _validate_numeric_type(device, 'device', int)
		
		current_ramp_speed_settings = {}
		for par in ['RUP', 'RDW']:
			current_ramp_speed_settings[par] = self.get_single_channel_parameter(parameter=par, channel=channel, device=device)
			self.set_single_channel_parameter(parameter=par, channel=channel, device=device, value=ramp_speed_VperSec)
		current_voltage = self.get_single_channel_parameter(parameter='VSET', channel=channel, device=device)
		expected_ramping_seconds = ((current_voltage-voltage)**2)**.5/ramp_speed_VperSec
		try:
			self.set_single_channel_parameter(
				parameter = 'VSET',
				channel = channel,
				device = device,
				value = voltage,
			)
			n_waited_seconds = 0
			while True: # Here I wait until it stabilizes.
				time.sleep(1)
				n_waited_seconds += 1
				if self.channel_status(channel = channel)['ramping up'] == 'no' and self.channel_status(channel = channel)['ramping down'] == 'no':
					break
				if n_waited_seconds > expected_ramping_seconds + timeout: # If this happens, better to raise an error that I cannot set the voltage. Otherwise this can be blocked forever.
					raise RuntimeError(f'Cannot reach a stable voltage after a timeout of {timeout} seconds.')
		except Exception as e:
			raise e
		finally:
			# Set back original configuration.
			for par in ['RUP', 'RDW']:
				self.set_single_channel_parameter(
					parameter = par,
					channel = channel,
					device = device,
					value = current_ramp_speed_settings[par],
				)
	
	def channel_status(self, channel: int, device: int=None):
		"""Returns the information from the status byte for the specified
		channel. Returns a dictionary containint the status byte and also
		some "human friendly" interpretations of the status byte."""
		if not isinstance(channel, int):
			raise TypeError(f'<channel> must be an integer number, received object of type {type(channel)}.')
		status_byte = int(self.query(CMD='MON', PAR='STAT',  CH=channel, BD=device)[-5:])
		status_byte_str = f"{status_byte:016b}"
		status_byte_str = status_byte_str[::-1]
		return {
			'status byte': status_byte,
			'output': 'on' if status_byte_str[0]=='1' else 'off',
			'ramping up': 'yes' if status_byte_str[1]=='1' else 'no',
			'ramping down': 'yes' if status_byte_str[2]=='1' else 'no',
			'there was overcurrent': 'yes' if status_byte_str[3]=='1' else 'no',
		}

	@property
	def model_name(self):
		if not hasattr(self, '_model_name'):
			response = self.query(CMD='MON', PAR='BDNAME')
			if check_successful_response(response) == False:
				raise RuntimeError(f'The instument responded with error: {response}.')
			self._model_name = response.split('VAL:')[-1]
		return self._model_name
	
	@property
	def serial_number(self):
		if not hasattr(self, '_serial_number'):
			response = self.query(CMD='MON', PAR='BDSNUM')
			if check_successful_response(response) == False:
				raise RuntimeError(f'The instument responded with error: {response}.')
			self._serial_number = response.split('VAL:')[-1]
		return self._serial_number

class OneCAENChannel:
	def __init__(self, caen, channel_number, device: int=None):
		"""A wrapper for a single channel of the CAEN power supply, to ease
		its usage and avoid confisuions with channel numbers."""
		_validate_type(caen, 'caen', CAENDesktopHighVoltagePowerSupply)
		_validate_numeric_type(channel_number, 'channel_number', int)
		if device is not None:
			_validate_numeric_type(device, 'device', int)
		self._caen = caen
		self._channel_number = channel_number
		self._device = device
	
	def set(self, PAR, VAL):
		VALID_PARs = {'VSET','ISET','MAXV','RUP','RDW','TRIP','PDWN','IMRANGE','ON','OFF','ZCADJ'}
		if PAR not in VALID_PARs:
			raise ValueError(f'<PAR> must be one of {VALID_PARs}. Refer to the user manual of the CAEN power supply for more information.')
		self._caen.set_single_channel_parameter(parameter=PAR, value=VAL, channel=self.channel_number, device=self._device)
	
	def get(self, PAR):
		return self._caen.get_single_channel_parameter(parameter=PAR, channel=self.channel_number, device=self._device)
	
	@property
	def belongs_to(self):
		return f'CAEN model {self._caen.model_name}, serial number {self._caen.serial_number}'
	
	@property
	def channel_number(self):
		return self._channel_number
	
	@property
	def V_mon(self):
		channel_polarity = self.polarity
		if channel_polarity == '+':
			polarity = 1
		elif channel_polarity == '-':
			polarity = -1
		else:
			raise RuntimeError(f'Unexpected polarity response from the insturment. I was expecting one of {{"+","-"}} but received instead {channel_polarity}.')
		return polarity*self.get(PAR='VMON')
	
	@property
	def I_mon(self):
		return 1e-6*self.get(PAR='IMON')
	
	@property
	def V_set(self):
		return self.get('VSET')
	@V_set.setter
	def V_set(self, voltage):
		_validate_numeric_type(voltage,'voltage',float)
		self.set(PAR='VSET',VAL=voltage)
	
	@property
	def polarity(self):
		return self.get(PAR='POL')
	
	@property
	def status_byte(self):
		return self._caen.channel_status(channel=self.channel_number, device=self._device)['status byte']
	@property
	def is_ramping(self):
		return self._caen.channel_status(channel=self.channel_number, device=self._device)['ramping up']=='yes' or self._caen.channel_status(channel=self.channel_number, device=self._device)['ramping down']=='yes'
	@property
	def there_was_overcurrent(self):
		return self._caen.channel_status(channel=self.channel_number, device=self._device)['there was overcurrent']=='yes'
	
	@property
	def output(self):
		return self._caen.channel_status(channel=self.channel_number, device=self._device)['output']
	@output.setter
	def output(self, output_status: str):
		_validate_type(output_status, 'output_status', str)
		output_status = output_status.lower()
		if output_status not in {'on','off'}:
			raise ValueError(f'<output_status> must be either "on" or "off", received {output_status}.')
		if output_status == 'on':
			self.set(PAR='ON',VAL=0)
		else:
			self.set(PAR='OFF',VAL=0)
	
	@property
	def current_compliance(self):
		return self.get('ISET')*1e-6
	@current_compliance.setter
	def current_compliance(self, amperes):
		_validate_numeric_type(amperes, 'amperes', float)
		self.set(PAR='ISET',VAL=1e6*amperes)
	
	def ramp_voltage(self, voltage, ramp_speed_VperSec: float = 5, timeout: float = 10):
		_validate_numeric_type(voltage, 'voltage', float)
		_validate_numeric_type(ramp_speed_VperSec, 'ramp_speed_VperSec', float)
		_validate_numeric_type(timeout, 'timeout', float)
		self._caen.ramp_voltage(voltage=voltage, channel=self.channel_number, device = self._device, ramp_speed_VperSec = ramp_speed_VperSec, timeout = timeout)
	
	def __str__(self):
		return f'Channel {self.channel_number} of {self.belongs_to}'
	
	def __repr__(self):
		return f'<{str(type(self))[1:-1]}, {self}>'
		
