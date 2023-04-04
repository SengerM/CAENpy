from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
import pandas
import plotly.express as px
import time
from digitizer import configure_digitizer, convert_dicitonaries_to_data_frame

if __name__ == '__main__':
	d = CAEN_DT5742_Digitizer(LinkNum=0)
	print('Connected with:',d.idn)

	configure_digitizer(d)

	# Data acquisition ---
	d.start_acquisition()
	time.sleep(.5) # Wait some time for the digitizer to trigger.
	d.stop_acquisition()
	waveforms = d.get_waveforms(get_ADCu_instead_of_volts=False) # Acquire the data.

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
	fig.write_html(f'plot.html')
