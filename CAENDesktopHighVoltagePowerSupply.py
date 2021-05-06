import serial
import platform

def create_command_string(BD, CMD, PAR, CH=None, VAL=None):
	command = f'$BD:{BD},CMD:{CMD},'
	if CH is not None:
		command += f'CH:{CH},'
	command += f'PAR:{PAR},'
	if VAL is not None:
		command += f'VAL:{VAL},'
	command = command[:-1] # Remove the last ','
	command += '\r\n'
	return command
	

class CAENDesktopHighVoltagePowerSupplyUSB:
	def __init__(self, port=None):
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
			timeout = 1,
		)
	
	def send_command(self, CMD, PAR, CH=None, VAL=None, BD=0):
		self.serial_port.write(create_command_string(BD=BD, CMD=CMD, PAR=PAR, CH=CH, VAL=VAL).encode('ASCII'))
	
	def read_response(self):
		return self.serial_port.read(9999).decode('ASCII')[:-2] # Remove the annoying '\r\n' in the end.
	
	def query(self, CMD, PAR, CH=None, VAL=None, BD=0):
		self.send_command(BD=BD, CMD=CMD, PAR=PAR, CH=CH, VAL=VAL)
		return self.read_response()

if __name__ == '__main__':
	source = CAENDesktopHighVoltagePowerSupplyUSB()
	print(source.query(CMD='MON', PAR='VSET', CH=0))
	
