import serial
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
	

class CAENDesktopHighVoltagePowerSupplyUSB:
	# This class was implemented according to the specifications in the 
	# user manual here: https://www.caen.it/products/dt1470et/
	def __init__(self, port=None, default_BD0=True):
		if default_BD0 not in [True, False]:
			raise ValueError(f'The argument <default_BD0> must be either True of False. Received {default_BD0}.')
		self.default_BD0 = default_BD0
		if port is None:
			if platform.system() == 'Linux':
				port = '/dev/ttyACM0' # According to the user manual, this is the default port in most Linux distributions. I am on Ubuntu and it is the case.
			else:
				raise ValueError(f'Please specify a serial port in which the CAEN device is connected.')
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
	
	def send_command(self, CMD, PAR, CH=None, VAL=None, BD=None):
		if BD is None:
			if self.default_BD0 == True:
				BD = 0
			else:
				raise ValueError(f'Please specify a value for the <BD> parameter. Refer to the CAEN user manual.')
		self.serial_port.write(create_command_string(BD=BD, CMD=CMD, PAR=PAR, CH=CH, VAL=VAL).encode('ASCII'))
	
	def read_response(self):
		return self.serial_port.readline().decode('ASCII')[:-2] # Remove the annoying '\r\n' in the end.
	
	def query(self, CMD, PAR, CH=None, VAL=None, BD=None):
		self.send_command(BD=BD, CMD=CMD, PAR=PAR, CH=CH, VAL=VAL)
		return self.read_response()
	
if __name__ == '__main__':
	source = CAENDesktopHighVoltagePowerSupplyUSB()
	print(source.query(CMD='MON', PAR='VSET', CH=0, BD=0))
	
