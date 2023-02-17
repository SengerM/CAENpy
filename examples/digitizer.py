from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
import numpy
import pandas
import plotly.express as px
import time

d = CAEN_DT5742_Digitizer(LinkNum=0)
print(d.idn)

# Digitizer configuration ---
d.set_sampling_frequency(MHz=5000)
d.set_record_length(1024)
d.set_max_num_events_BLT(2) # 2 events per call to `d.get_waveforms`.
d.set_acquisition_mode('sw_controlled')
d.set_ext_trigger_input_mode('disabled')
d.write_register(0x811C, 0x000D0001) # Enable busy signal on GPO.
d.set_fast_trigger_mode(enabled=True)
d.set_fast_trigger_digitizing(enabled=True)
d.enable_channels(group_1=True, group_2=True)
for ch in [0,1]:
	d.set_trigger_polarity(channel=ch, edge='falling')
d.set_fast_trigger_DC_offset(DAC=32768)
d.set_fast_trigger_threshold(24000)
d.set_post_trigger_size(50)

for n_acquisition in range(11):
	print(f'n_acquisition = {n_acquisition}')
	# Data acquisition ---
	with d:
		waveforms = d.get_waveforms(get_ADCu_instead_of_volts=False) # Acquire the data.
	
	# Data analysis and plotting ---
	if len(waveforms) == 0:
		raise RuntimeError('Could not acquire any event. The reason may be that you dont have anything connected to the inputs of the digitizer, or a wrong trigger threshold and/or offset setting.')

	data = []
	for n_event in waveforms:
		for n_channel in waveforms[n_event]:
			df = pandas.DataFrame(waveforms[n_event][n_channel])
			df['n_event'] = n_event
			df['n_channel'] = n_channel
			df.set_index(['n_event','n_channel'], inplace=True)
			data.append(df)
	data = pandas.concat(data)

	print('Acquired data is:')
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
