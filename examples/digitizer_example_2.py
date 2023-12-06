from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
import pandas
import plotly.express as px
import time
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame
from pathlib import Path

if __name__ == '__main__':
	d = CAEN_DT5742_Digitizer(LinkNum=0)
	print('Connected with:',d.idn)

	configure_digitizer(d)
	d.set_max_num_events_BLT(3) # Override the maximum number of events to be stored in the digitizer's self buffer.

	# Data acquisition ---
	with d:
		print(f'Digitizer is enabled! Waiting 1 second for it to trigger...')
		time.sleep(1) # Wait some time for the digitizer to trigger.
	# At this point there should be 3 events in the digitizer (provided at least 3 trigger signals went into the trigger input).
	
	print(f'Reading data from the digitizer...')
	waveforms = d.get_waveforms()

	# Data analysis and plotting ---
	if len(waveforms) == 0:
		raise RuntimeError('Could not acquire any event. The reason may be that you dont have anything connected to the inputs of the digitizer, or a wrong trigger threshold and/or offset setting.')

	data = convert_dicitonaries_to_data_frame(waveforms)

	print('Acquired data is:')
	print(data)

	fig = px.line(
		title = 'CAEN digitizer testing',
		data_frame = data.reset_index(),
		x = 'Time (s)',
		y = 'Amplitude (V)',
		color = 'n_channel',
		facet_row = 'n_event',
		markers = True,
	)
	path_to_plot = (Path(__file__).parent/'plot.html').resolve()
	fig.write_html(path_to_plot, include_plotlyjs='cdn')
	print(f'A plot with the waveforms can be found in {path_to_plot}')
