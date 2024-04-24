from CAENpy.CAENDesktopHighVoltagePowerSupply import CAENDesktopHighVoltagePowerSupply
import time

caen = CAENDesktopHighVoltagePowerSupply(port='/dev/ttyACM0') # Open the connection.
print('Connected with: ', caen.idn) # This should print the name and serial number of the CAEN.

# Control each channel manually:
print('Ramping voltage up...')
caen.channels[0].ramp_voltage(44, ramp_speed_VperSec=5) # Increase the voltage.
print('V = ', caen.channels[0].V_mon, ' V') # Measure the voltage.
print('I = ', caen.channels[0].I_mon, ' A') # Measure the current.
caen.channels[0].ramp_voltage(0) # Go back to 0 V.
print('V = ', caen.channels[0].V_mon, ' V')

# Loop over the channels:
for n_channel,channel in enumerate(caen.channels):
	print(f'##################')
	channel.ramp_voltage(voltage=11*(n_channel+1), ramp_speed_VperSec=5) # Ramp voltage and freeze program execution until finished.
	print(f'Set voltage channel {n_channel}: {channel.V_set} V')
	print(f'Measured voltage channel {n_channel}: {channel.V_mon} V')
	print(f'Set current channel {n_channel}: {channel.current_compliance} A')
	print(f'Measured current channel {n_channel}: {channel.I_mon} A')
	channel.V_set = 0 # Set the voltage to 0 without freezing program flow, voltage will ramp according to the settings in the CAEN, which of course you can change remotely using CAENpy as well.