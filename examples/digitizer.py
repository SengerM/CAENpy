from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from ctypes import *
import numpy
import pandas
import plotly.express as px

d = CAEN_DT5742_Digitizer(LinkNum=0)
d.reset()

print('###')
info = d.get_info()
for key in sorted(info):
	print(f'{key}: {info[key]}')
print('###')

d.set_sampling_frequency(MHz=5000)
d.set_record_length(1024)
d.set_max_num_events_BLT(2)
d.set_acquisition_mode('sw_controlled')
d.set_ext_trigger_input_mode('disabled')
d.write_register(0x811C, 0x000D0001) # Enable busy signal on GPO.
d.set_fast_trigger_mode(enabled=True)
d.set_fast_trigger_digitizing(enabled=True)
d.enable_channels(group_1=True, group_2=True)
for ch in [0,1]:
	d.set_trigger_polarity(channel=ch, edge='rising')
d.set_fast_trigger_DC_offset(32768)
d.set_fast_trigger_threshold(24000)
d.set_post_trigger_size(30)

status = d.get_acquisition_status()
print(f"Digitizer status is {status:#04X} (OK is 0x180)" )

with d:
	d.read_data()
	n_events = d.get_number_of_events()
	
	for n_event in range(n_events):
		event, event_info = d.get_event(n_event)
		
		event_waveforms = []
		for j in range(18):
			group = int(j / 9)
			if event.GrPresent[group] != 1:
				continue # If this group was disabled then skip it

			channel = j - (9 * group)
			block = event.DataGroup[group]
			size = block.ChSize[channel]
			
			wf = pandas.DataFrame(
				{
					'sample': numpy.array([int(block.DataChannel[channel][_]) for _ in range(size)]),
					'time': numpy.array(range(size)),
				}
			)
			wf['channel'] = channel
			event_waveforms.append(wf)
		event_waveforms = pandas.concat(event_waveforms)
		print(event_waveforms)
		fig = px.line(
			data_frame = event_waveforms,
			x = 'time',
			y = 'sample',
			color = 'channel',
			markers = True,
		)
		fig.write_html('plot.html')
		input('Continue?')
	
	print('Finishing...')
