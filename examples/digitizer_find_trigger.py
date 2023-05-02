from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
import pandas
import plotly.express as px
import time
from digitizer import configure_digitizer, convert_dicitonaries_to_data_frame

def interlaced(lst):
	# https://en.wikipedia.org/wiki/Interlacing_(bitmaps)
	lst = sorted(lst)[::-1]
	if len(lst) == 1:
		return lst
	result = [lst[0], lst[-1]]
	ranges = [(1, len(lst) - 1)]
	for start, stop in ranges:
		if start < stop:
			middle = (start + stop) // 2
			result.append(lst[middle])
			ranges += (start, middle), (middle + 1, stop)
	return result

if __name__ == '__main__':
	import time
	
	TIME_WINDOW_SECONDS = 11
	OFILENAME = 'deleteme.csv'
	
	d = CAEN_DT5742_Digitizer(LinkNum=0)
	print('Connected with:',d.idn)

	configure_digitizer(d)

	d.set_max_num_events_BLT(999)

	with open(OFILENAME, 'w') as ofile:
		print(f'fast_trigger_threshold,n_triggers_in_{TIME_WINDOW_SECONDS}_seconds', file=ofile)
	for threshold in interlaced(range(26300,26800)):
		d.set_fast_trigger_threshold(threshold)
		with d:
			time.sleep(TIME_WINDOW_SECONDS) # Give some time to record some triggers.
			waveforms = d.get_waveforms(get_ADCu_instead_of_volts=False) # Acquire the data.
		print(threshold, len(waveforms))
		with open(OFILENAME, 'a') as ofile:
			print(f'{threshold},{len(waveforms)}', file=ofile)
