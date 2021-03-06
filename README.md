# CAENpy

Easily control [CAEN](https://www.caen.it/) equipment with pure Python.

![Picture of a CAEN power supply](https://www.caen.it/wp-content/uploads/2017/10/DT1471HET_g.jpg)

## Installation

```
pip3 install git+https://github.com/SengerM/CAENpy
```

## Usage

The communication with the device is done via the `set_single_channel_parameter` and `get_single_channel_parameter` methods. 

Simple usage example:

```Python
from CAENpy.CAENDesktopHighVoltagePowerSupply import CAENDesktopHighVoltagePowerSupply
import time

caen = CAENDesktopHighVoltagePowerSupply(ip='130.60.165.238', timeout=10) # Increase timeout for slow networks.
# caen = CAENDesktopHighVoltagePowerSupply(port='/dev/ttyACM0') # You can also connect via USB (name of port changes in different operating systems, check the user manual of your device).

# Check that the connection was successful: 
print(f'Model: {caen.model_name}, serial #: {caen.serial_number}') # Print model name and serial number, example: 'Model: DT1470ET, serial #: 13398'.

caen.set_single_channel_parameter(parameter='ON', channel=0, value=None)
for v in range(22):
	caen.set_single_channel_parameter( # This does not block execution! You have to manually wait the required time until the voltage is changed.
		parameter = 'VSET', 
		channel = 0, 
		value = float(v),
	)
	print(f'VMON = {caen.get_single_channel_parameter(parameter="VMON", channel=0)} | IMON = {caen.get_single_channel_parameter(parameter="IMON", channel=0)}')
	time.sleep(1)
caen.set_single_channel_parameter(parameter='OFF', channel=0, value=None)
```
Note that in the previous example **the execution is not blocked while the voltage is being changed**, because the ramp feature is implemented in the CAEN power supplies themselves. If you want to automatically block the execution of your code until the voltage has been smoothly ramped to the final value, use the method `ramp_voltage`. Example:
```Python
from CAENpy.CAENDesktopHighVoltagePowerSupply import CAENDesktopHighVoltagePowerSupply

caen = CAENDesktopHighVoltagePowerSupply(ip='130.60.165.238', timeout=10) # Increase timeout for slow networks.
# caen = CAENDesktopHighVoltagePowerSupply(port='/dev/ttyACM0') # You can also connect via USB (name of port changes in different operating systems, check the user manual of your device).

caen.set_single_channel_parameter(parameter='ON', channel=0, value=None)
for v in range(22):
	caen.ramp_voltage( # This blocks the execution until the VMON (i.e. measured voltage) is stable, so you don't have to manually wait/check that it has reached the final voltage.
		voltage = v,
		channel = 0,
		ramp_speed_VperSec = 1, # Default is 5 V/s.
	)
	print(f'VMON = {caen.get_single_channel_parameter(parameter="VMON", channel=0)} | IMON = {caen.get_single_channel_parameter(parameter="IMON", channel=0)}')
caen.set_single_channel_parameter(parameter='OFF', channel=0, value=None)
```
