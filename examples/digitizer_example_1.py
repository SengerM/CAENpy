from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
import pandas
import numpy
import time

def configure_digitizer(digitizer:CAEN_DT5742_Digitizer):
	digitizer.set_sampling_frequency(MHz=5000)
	digitizer.set_record_length(1024)
	digitizer.set_max_num_events_BLT(4)
	digitizer.set_acquisition_mode('sw_controlled')
	digitizer.set_ext_trigger_input_mode('disabled')
	digitizer.write_register(0x811C, 0x000D0001) # Enable busy signal on GPO.
	digitizer.set_fast_trigger_mode(enabled=True)
	digitizer.set_fast_trigger_digitizing(enabled=True)
	digitizer.enable_channels(group_1=True, group_2=True)
	digitizer.set_fast_trigger_threshold(22222)
	digitizer.set_fast_trigger_DC_offset(V=0)
	digitizer.set_post_trigger_size(0)
	for ch in [0,1]:
		digitizer.set_trigger_polarity(channel=ch, edge='rising')

def convert_dicitonaries_to_data_frame(waveforms:dict):
	data = []
	for n_event,event_waveforms in enumerate(waveforms):
		for n_channel in event_waveforms:
			df = pandas.DataFrame(event_waveforms[n_channel])
			df['n_event'] = n_event
			df['n_channel'] = n_channel
			df.set_index(['n_event','n_channel'], inplace=True)
			data.append(df)
	return pandas.concat(data)

if __name__ == '__main__':
	d = CAEN_DT5742_Digitizer(LinkNum=0)
	print('Connected with:',d.idn)

	configure_digitizer(d)
	d.set_max_num_events_BLT(1024) # Override the maximum number of events to be stored in the digitizer's self buffer.
	
	# Data acquisition ---
	n_events = 0
	ACQUIRE_AT_LEAST_THIS_NUMBER_OF_EVENTS = 2222
	data = []
	with d: # Enable digitizer to take data
		print('Digitizer is enabled! Acquiring data...')
		while n_events < ACQUIRE_AT_LEAST_THIS_NUMBER_OF_EVENTS:
			time.sleep(.05)
			waveforms = d.get_waveforms() # Acquire the data.
			this_readout_n_events = len(waveforms)
			n_events += this_readout_n_events
			data += waveforms
			print(f'{n_events} out of {ACQUIRE_AT_LEAST_THIS_NUMBER_OF_EVENTS} were acquired.')
		print(f'A total of {n_events} were acquired, finishing acquisition and stopping digitizer.')
	
	print(f'Creating a pandas data frame with the data...')
	data = convert_dicitonaries_to_data_frame(data)

	print('Acquired data is:')
	print(data)
	# The previous line should print something like this:
	#
	#	                         Amplitude (V)      Time (s)
	#	n_event n_channel                                   
	#	0       CH0                   0.019902 -1.626000e-07
	#			CH0                   0.019902 -1.624000e-07
	#			CH0                   0.019662 -1.622000e-07
	#			CH0                   0.021121 -1.620000e-07
	#			CH0                   0.020635 -1.618000e-07
	#	...                                ...           ...
	#	1023    trigger_group_1       0.026258  4.120000e-08
	#			trigger_group_1       0.026986  4.140000e-08
	#			trigger_group_1       0.027227  4.160000e-08
	#			trigger_group_1       0.026986  4.180000e-08
	#			trigger_group_1       0.027718  4.200000e-08
	#	
	#	[18874368 rows x 2 columns]
