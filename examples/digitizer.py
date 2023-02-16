from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from ctypes import *
import numpy
import pandas
import plotly.express as px

def pretty(d, indent=0):
	for key, value in d.items():
		print('\t' * indent + str(key))
		if isinstance(value, dict):
			pretty(value, indent+1)
		else:
			print('\t' * (indent+1) + str(value))

d = CAEN_DT5742_Digitizer(LinkNum=0)
d.reset()

print(d.idn)

d.set_sampling_frequency(MHz=5000)
d.set_record_length(1024)
d.set_max_num_events_BLT(1)
d.set_acquisition_mode('sw_controlled')
d.set_ext_trigger_input_mode('disabled')
# ~ d.write_register(0x811C, 0x000D0001) # Enable busy signal on GPO.
d.set_fast_trigger_mode(enabled=True)
d.set_fast_trigger_digitizing(enabled=True)
d.enable_channels(group_1=True, group_2=True)
for ch in [0,1]:
	d.set_trigger_polarity(channel=ch, edge='rising')
d.set_fast_trigger_DC_offset(32768)
d.set_fast_trigger_threshold(24000)
d.set_post_trigger_size(30)

with d:
	waveforms = d.get_waveforms() # Acquire the data.
	
data = []
for n_event in waveforms:
	for n_channel in waveforms[n_event]:
		df = pandas.DataFrame(waveforms[n_event][n_channel])
		df['n_event'] = n_event
		df['n_channel'] = n_channel
		df.set_index(['n_event','n_channel'], inplace=True)
		data.append(df)
data = pandas.concat(data)
print(data)
fig = px.line(
	data_frame = data.reset_index(),
	x = 'Time (s)',
	y = 'Amplitude (V)',
	color = 'n_channel',
	facet_row = 'n_event',
	markers = True,
)
fig.write_html('plot.html')
