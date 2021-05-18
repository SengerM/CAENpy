# CAENpy

Easily control [CAEN](https://www.caen.it/) equipment with pure Python. 

## Installation

```
pip3 install git+https://github.com/SengerM/CAENpy
```

## Usage

Usage example:

```Python
from CAENpy.CAENDesktopHighVoltagePowerSupply import CAENDesktopHighVoltagePowerSupply
import time

caen = CAENDesktopHighVoltagePowerSupply(ip='130.60.165.238', timeout=10) # Increase timeout for slow networks.
caen.set_single_channel_parameter(parameter='ON', channel=0, value=None)
for v in [i for i in range(22)]:
	caen.set_single_channel_parameter(parameter='VSET', channel=0, value=float(v))
	print(f'VMON = {caen.get_single_channel_parameter(parameter="VMON", channel=0)} | IMON = {caen.get_single_channel_parameter(parameter="IMON", channel=0)}')
	time.sleep(1)
caen.set_single_channel_parameter(parameter='OFF', channel=0, value=None)
```
