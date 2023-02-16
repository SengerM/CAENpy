# CAEN DT5742 control module, not all original libCAENDigitizer features supported.

# ~ This file was taken and adapted from https://github.com/LucaMenzio/UFSD_DigiDAQ

from ctypes import *
import time

libCAENDigitizer = CDLL('/usr/lib/libCAENDigitizer.so') # Change the path according to your installation. This is the default one in Ubuntu 22.04. The official library can be found here https://www.caen.it/products/caendigitizer-library/

CAEN_DGTZ_DRS4Frequency_MEGA_HERTZ = {
	750: 3,
	1000: 2,
	2500: 1,
	5000: 0
}
CAEN_DGTZ_TriggerMode = {
	'disabled': 0,
	'extout only': 2,
	'acquisition only': 1,
	'acquisition and extout': 3,
}

def check_error_code(code):
	"""Check if the code returned by a function of the libCAENDigitizer
	library is an error or not. If it is not an error, nothing is done,
	if it is an error, a `RuntimeError` is raised with the error code.
	"""
	if code != 0:
		raise RuntimeError(f'libCAENDigitizer has returned error code {code}.')

def struct2dict(struct):
	return dict((field, getattr(struct, field)) for field, _ in struct._fields_)

class BoardInfo(Structure):
	_fields_ = [
		("ModelName", c_char*12),
		("Model", c_uint32),
		("Channels", c_uint32),
		("FormFactor", c_uint32),
		("FamilyCode", c_uint32),
		("ROC_FirmwareRel", c_char*20),
		("AMC_FirmwareRel", c_char*40),
		("SerialNumber", c_uint32),
		("MezzanineSerNum", (c_char*8)*4),
		("PCB_Revision", c_uint32),
		("ADC_NBits", c_uint32),
		("SAMCorrectionDataLoaded", c_uint32),
		("CommHandle", c_int),
		("VMEHandle", c_int),
		("License", c_char*999),
	]
	
class Group(Structure):
	_fields_ = [
		("ChSize", c_uint32*9),
		("DataChannel", POINTER(c_float)*9),
		("TriggerTimeLag", c_uint32),
		("StartIndexCell", c_uint16)]

class Event(Structure):
	_fields_ = [
		("GrPresent", c_uint8*4),
		("DataGroup", Group*4)]

class EventInfo(Structure):
	_fields_ = [
		("EventSize", c_uint32),
		("BoardId", c_uint32),
		("Pattern", c_uint32),
		("ChannelMask", c_uint32),
		("EventCounter", c_uint32),
		("TriggerTimeTag", c_uint32)]

class CAEN_DT5742_Digitizer:
	def __init__(self, LinkNum:int):
		self._connected = False
		self._LinkNum = LinkNum
		self.__handle = c_int() # Handle object, keep track of our connection.
		
		# These are some objects required by the libCAENDigitizer.
		self.eventObject = POINTER(Event)()# Stores the event that's currently being processed. Is overwritten by the next event as soon as decodeEvent() is called.
		self.eventPointer = POINTER(c_char)() # Points to the event that's currently being processed.
		self.eventInfo = EventInfo() # Stores some stats about the event that's currently being processed.
		self.eventBuffer = POINTER(c_char)() # Stores the last block of events transferred from the digitizer.
		self.eventAllocatedSize = c_uint32() # Size in memory of the event object.
		self.eventBufferSize = c_uint32() # Size in memory of the events' block transfer.
		self.eventVoidPointer = cast(byref(self.eventObject), POINTER(c_void_p)) # Need to create a **void since technically speaking other kinds of Event() esist as well (the CAENDigitizer library supports a multitude of devices, with different Event() structures) and we need to pass this to "universal" methods.
		
		self._open() # Open the connection to the digitizer.
	
	def __enter__(self):
		self._allocateEvent()
		self._mallocBuffer()
		self._start_acquisition()

	def __exit__(self, exc_type, exc_val, exc_tb):
		self._stop_acquisition()
		self._freeEvent()
		self._freeBuffer()
	
	def __del__(self):
		self._close()
	
	def _open(self):
		"""Open the connection to the digitizer."""
		if self._connected == False:
			code = libCAENDigitizer.CAEN_DGTZ_OpenDigitizer(
				c_long(0), # LinkType (0 is USB).
				c_int(self._LinkNum),
				c_int(0), # ConetNode.
				c_uint32(0), # VMEBaseAddress.
				byref(self.__handle)
			)
			check_error_code(code)
			self._connected = True
	
	def _close(self):
		"""Close the connection with the digitizer."""
		if self._connected == True:
			code = libCAENDigitizer.CAEN_DGTZ_CloseDigitizer(self.__handle) # Most of the times this line produces a `Segmentation fault (core dumped)`...
			check_error_code(code)
			self._connected = False
	
	def _get_handle(self):
		"""Get the connection handle in a safe way no matter the connection
		status."""
		if self._connected == True:
			return self.__handle
		else:
			raise RuntimeError(f'The connection with the CAEN Digitizer is not open!')
	
	def reset(self):
		"""Reset the digitizer."""
		code = libCAENDigitizer.CAEN_DGTZ_Reset(self._get_handle())
		check_error_code(code)

	def write_register(self, address, data):
		"""Write data to a given register. It is advised by the manual
		of the CAENDigitizer library that one should avoid using this
		function, and use the specific functions instead."""
		code = libCAENDigitizer.CAEN_DGTZ_WriteRegister(
			self._get_handle(), 
			c_uint32(address), 
			c_uint32(data)
		)
		check_error_code(code)

	def read_register(self, address):
		"""Read bytes from a specific register. Returns the data in the
		register as an `int` object."""
		if not isinstance(address, int) or not 0 <=address<2**16:
			raise ValueError(f'`address` must be a 16 bit integer, received {repr(address)}. ')
		data = c_uint32()
		code = libCAENDigitizer.CAEN_DGTZ_ReadRegister(
			self._get_handle(), 
			c_uint32(address), 
			byref(data),
		)
		check_error_code(code)
		return data.value

	def set_acquisition_mode(self, mode:str):
		"""Set the acquisition mode.
		
		Arguments
		---------
		mode: str
			Specifies the acquisition mode, see CAENDigitizer library
			manual for details. Options are `'sw_controlled', `'in_controlled'`
			and `'first_trg_controlled'`.
			
		"""
		MODES = {'sw_controlled': 0, 'in_controlled': 1, 'first_trg_controlled': 2}
		if mode not in MODES:
			raise ValueError(f'`mode` must be one of {set(MODES.keys())}, received {repr(mode)}. ')
		code = libCAENDigitizer.CAEN_DGTZ_SetAcquisitionMode(
			self._get_handle(), 
			c_long(MODES[mode]),
		)
		check_error_code(code)

	def get_info(self)->dict:
		"""Get information related to the board such as serial number, etc."""
		info = BoardInfo()
		code = libCAENDigitizer.CAEN_DGTZ_GetInfo(
			self._get_handle(), 
			byref(info)
		)
		check_error_code(code)
		return struct2dict(info)

	def _allocateEvent(self):
		"""Allocate space in memory for the event object."""
		code = libCAENDigitizer.CAEN_DGTZ_AllocateEvent(
			self._get_handle(), 
			self.eventVoidPointer
		)
		check_error_code(code)

	def _mallocBuffer(self):
		"""Allocate space in memory for the events' block transfer."""
		code = libCAENDigitizer.CAEN_DGTZ_MallocReadoutBuffer(
			self._get_handle(), 
			byref(self.eventBuffer),
			byref(self.eventAllocatedSize)
		)
		check_error_code(code)

	def _freeEvent(self):
		"""Free memory that was allocated for the event object."""
		ptr = cast(pointer(self.eventObject), POINTER(c_void_p))
		code = libCAENDigitizer.CAEN_DGTZ_FreeEvent(
			self._get_handle(), 
			ptr
		)
		check_error_code(code)

	def _freeBuffer(self):
		"""Free memory that was allocated for the events' block transfer."""
		code = libCAENDigitizer.CAEN_DGTZ_FreeReadoutBuffer(byref(self.eventBuffer))
		check_error_code(code)

	def set_max_num_events_BLT(self, numEvents):
		"""Max number of events per block transfer. Minimum is 1, maximum
		is 1023. It's recommended to set it to the maximum allowed value 
		and continuously poll the digitizer for new data. Binary transfer
		is fast while a full buffer means the digitizer	will discard events.
		"""
		
		code = libCAENDigitizer.CAEN_DGTZ_SetMaxNumEventsBLT(
			self._get_handle(),
			c_uint32(numEvents)
		)
		check_error_code(code)

	def get_acquisition_status(self):
		"""Reads and returns the 'Acquisition Status' register."""
		# Wait - read - wait - read to clear registers and get digitizer's status. Funny but works.
		time.sleep(0.3)
		self.read_register(0x8104)
		time.sleep(0.2)
		return self.read_register(0x8104)

	def set_fast_trigger_mode(self, enabled:bool):
		"""Enable or disable the TRn as the local trigger in the x742 series.
		
		Arguments
		---------
		enabled: bool
			True or false to enable or disable.
		"""
		if not isinstance(enabled, bool):
			raise TypeError(f'`enabled` must be of type {repr(bool)}, received object of type {repr(type(enabled))} instead.')
		code = libCAENDigitizer.CAEN_DGTZ_SetFastTriggerMode(
			self._get_handle(), 
			c_long(0 if enabled == False else 1)
		)
		check_error_code(code)

	def set_fast_trigger_digitizing(self, enabled:bool):
		"""Regarding the x742 series, enables/disables (set) the presence
		of the TRn signal in the data readout.
		
		Arguments
		---------
		enabled: bool
			True or false to enable or disable.
		"""
		if not isinstance(enabled, bool):
			raise TypeError(f'`enabled` must be of type {repr(bool)}, received object of type {repr(type(enabled))} instead.')
		code = libCAENDigitizer.CAEN_DGTZ_SetFastTriggerDigitizing(
			self._get_handle(), 
			c_long(0 if enabled == False else 1)
		)
		check_error_code(code)

	def set_fast_trigger_DC_offset(self, offset:int):
		"""Set the DC offset for the trigger channel TRn.
		
		Arguments
		---------
		offset: int
			Value for the offset, in ADC units between 0 and 2**16-1 (65535).
		"""
		if not isinstance(offset, int) or not 0 <= offset < 2**16:
			raise ValueError(f'`offset` must be an integer number between 0 and 2**16-1.')
		code = libCAENDigitizer.CAEN_DGTZ_SetGroupFastTriggerDCOffset(
			self._get_handle(), 
			c_uint32(0), # This is for the 'group', not sure what it is but it is always 0 for us.
			c_uint32(offset)
		)
		check_error_code(code)

	def set_fast_trigger_threshold(self, threshold:int):
		"""Set the fast trigger threshold.
		
		Arguments
		---------
		threshold: int
			Threshold value in ADC units, between 0 and 2**16-1 (65535).
		"""
		if not isinstance(threshold, int) or not 0 <= threshold < 2**16:
			raise ValueError(f'`threshold` must be an integer number between 0 and 2**16-1.')
		code = libCAENDigitizer.CAEN_DGTZ_SetGroupFastTriggerThreshold(
			self._get_handle(), 
			c_uint32(0), # This is for the 'group', not sure what it is but it is always 0 for us.
			c_uint32(threshold)
		)
		check_error_code(code)

	def set_post_trigger_size(self, percentage:int):
		"""Set the 'post trigger size', i.e. the position of the trigger
		within the acquisition window.
		
		Arguments
		---------
		percentage: int
			Percentage of the record length. 0 % means that the trigger 
			is at the end of the window, while 100 % means that it is at
			the beginning.
		"""
		if not isinstance(percentage, int) or not 0 <= percentage <= 100:
			raise ValueError(f'`percentage` must be an integer number between 0 and 100.')
		code = libCAENDigitizer.CAEN_DGTZ_SetPostTriggerSize(
			self._get_handle(), 
			c_uint32(percentage),
		)
		check_error_code(code)

	def set_record_length(self, length:int):
		"""Set how many samples should be taken for each event.
		Arguments 
		---------
		length: int
			The size of the record (in samples).
		"""
		code = libCAENDigitizer.CAEN_DGTZ_SetRecordLength(
			self._get_handle(), 
			c_uint32(length),
		)
		check_error_code(code)

	def set_ext_trigger_input_mode(self, mode:str):
		"""Enable or disable the external trigger (TRIG IN).
		
		Arguments
		---------
		mode: str
			One of `'disabled'`, `'extout only'`, `'acquisition only'`,
			`'acquisition and extout'`.
		"""
		if mode not in CAEN_DGTZ_TriggerMode:
			raise ValueError(f'`mode` must be one of {set(CAEN_DGTZ_TriggerMode.keys())}, received {repr(mode)}. ')
		code = libCAENDigitizer.CAEN_DGTZ_SetExtTriggerInputMode(
			self._get_handle(), 
			c_long(CAEN_DGTZ_TriggerMode[mode])
		)
		check_error_code(code)

	def set_trigger_polarity(self, channel:int, edge:str):
		"""Set the trigger polarity of a specified channel.
		
		Arguments
		---------
		channel: int
			Number of channel.
		edge: str
			Either `'rising'` or `'falling'`.
		"""
		EDGE_VALUES = {'rising','falling'}
		if edge not in EDGE_VALUES:
			raise ValueError(f'`edge` must be one of {EDGE_VALUES}, received {repr(edge)}. ')
		code = libCAENDigitizer.CAEN_DGTZ_SetTriggerPolarity(
			self._get_handle(), 
			c_uint32(channel), 
			c_long(0 if edge == 'rising' else 1),
		)
		check_error_code(code)

	def set_sampling_frequency(self, MHz:int):
		"""Set the sampling frequency of the digitizer.
		
		Arguments
		---------
		MHz: int
			The sampling frequency in Mega Hertz. Note that only some
			discrete values are allowed, which are 750, 1000, 2500 and 5000.
		"""
		
		FREQUENCY_VALUES = CAEN_DGTZ_DRS4Frequency_MEGA_HERTZ
		if MHz not in FREQUENCY_VALUES:
			raise ValueError(f'`MHz` must be one of {set(FREQUENCY_VALUES.keys())}, received {repr(MHz)}. ')
		code = libCAENDigitizer.CAEN_DGTZ_SetDRS4SamplingFrequency(
			self._get_handle(), 
			c_long(FREQUENCY_VALUES[MHz]),
		)
		check_error_code(code)

	def enable_channels(self, group_1:bool, group_2:bool):
		"""Set which groups to enable and/or disable.
		
		Arguments
		---------
		group_1: bool
			Enable or disable group 1, i.e. channels 0, 1, ..., 7.
		group_2: bool
			Enable or disable group 2, i.e. channels 8, 9, ..., 15.
		"""
		mask = 0
		for i,group in enumerate([group_1, group_2]):
			mask |= (1 if group else 0) << i
		code = libCAENDigitizer.CAEN_DGTZ_SetGroupEnableMask(
			self._get_handle(), 
			c_uint32(mask),
		)
		check_error_code(code)

	def set_channel_DC_offset(self, channel:int, offset:int):
		"""
		Set the DC offset for a channel.
		Arguments
		---------
		channel: int
			Number of the channel to set the offset.
		offset: int
			Value for the offset, in ADC units between 0 and 2**16-1 (65535).
		"""
		if not isinstance(offset, int) or not 0 <= offset < 2**16:
			raise ValueError(f'`offset` must be an integer number between 0 and 2**16-1.')
		if not isinstance(channel, int) or not 0 <= channel < 16:
			raise ValueError(f'`channel` must be 0, 1, ..., 15, received {repr(channel)}. ')
		code = libCAENDigitizer.CAEN_DGTZ_SetChannelDCOffset(
			self._get_handle(), 
			c_uint32(channel), 
			c_uint32(offset),
		)
		check_error_code(code)

	def get_channel_DC_offset(self, channel):
		"""Get the DC offset value for a channel.
		
		Arguments
		---------
		channel: int
			Number of channel.
		"""
		if not isinstance(channel, int) or not 0 <= channel < 16:
			raise ValueError(f'`channel` must be 0, 1, ..., 15, received {repr(channel)}. ')
		value = c_uint32(0)
		code = libCAENDigitizer.CAEN_DGTZ_GetChannelDCOffset(
			self._get_handle(), 
			c_uint32(channel), 
			byref(value),
		)
		check_error_code(code)
		return value.value

	def _start_acquisition(self):
		"""Start the acquisition in the board. The RUN LED will turn on."""
		code = libCAENDigitizer.CAEN_DGTZ_SWStartAcquisition(self._get_handle())
		check_error_code(code)

	def _stop_acquisition(self):
		"""Stop the acquisition. The RUN LED will turn off."""
		code = libCAENDigitizer.CAEN_DGTZ_SWStopAcquisition(self._get_handle())
		check_error_code(code)

	def _read_data(self):
		"""Reads data from the digitizer into the computer."""
		code = libCAENDigitizer.CAEN_DGTZ_ReadData(
			self._get_handle(), 
			c_long(0), 
			self.eventBuffer,
			byref(self.eventBufferSize)
		)
		check_error_code(code)

	def get_number_of_events(self):
		"""Get the number of events contained in the last block transfer
		initiated."""
		eventNumber = c_uint32()
		code = libCAENDigitizer.CAEN_DGTZ_GetNumEvents(
			self._get_handle(),
			self.eventBuffer, 
			self.eventBufferSize,
			byref(eventNumber)
		)
		check_error_code(code)
		return eventNumber.value

	def get_event_info(self, n_event:int):
		"""Fill the eventInfo object declared in __init__ with stats from
		the i-th event in the buffer (and thus from the last block transfer).
		At the end of this function eventPointer will point to the i-th event.
		
		Arguments
		---------
		n_event: int
			Number of event to get the event info.
		
		Returns
		-------
		event_info
			An object with information about this event.
		"""
		code = libCAENDigitizer.CAEN_DGTZ_GetEventInfo(
			self._get_handle(), 
			self.eventBuffer, 
			self.eventBufferSize, 
			c_uint32(n_event),
			byref(self.eventInfo), 
			byref(self.eventPointer)
		)
		check_error_code(code)
		return self.eventInfo

	def decode_event(self):
		"""Decode the event in eventPointer and put all data in the eventObject
		created in __init__. eventPointer is filled by calling getEventInfo first.
		"""
		code = libCAENDigitizer.CAEN_DGTZ_DecodeEvent(
			self._get_handle(), 
			self.eventPointer, 
			self.eventVoidPointer
		)
		check_error_code(code)
		return self.eventObject.contents

	def get_event(self, index):
		"""Get event data."""
		info = self.get_event_info(index)
		event = self.decode_event()
		return event, info

	def load_correction_data(self, MHz:int):
		"""Load correction tables from digitizer's memory at right frequency.
		
		Arguments
		---------
		MHz: int
			The sampling frequency in Mega Hertz. Note that only some
			discrete values are allowed, which are 750, 1000, 2500 and 5000.
		"""
		FREQUENCY_VALUES = CAEN_DGTZ_DRS4Frequency_MEGA_HERTZ
		if MHz not in FREQUENCY_VALUES:
			raise ValueError(f'`MHz` must be one of {set(FREQUENCY_VALUES.keys())}, received {repr(MHz)}. ')
		code = libCAENDigitizer.CAEN_DGTZ_LoadDRS4CorrectionData(
			self._get_handle(), 
			c_long(FREQUENCY_VALUES[MHz])
		)
		check_error_code(code)

	def DRS4_correction(self, enable:bool):
		"""Enable raw data correction using tables loaded with loadCorrectionData.
		This corrects for slight differences in ADC capacitors' values and
		different latency between the two groups' circutry. Refer to manual for
		more.
		"""
		if not isinstance(enable, bool):
			raise ValueError(f'`enable` must be an instance of {repr(bool)}, received object of type {repr(type(enable))}.')
		if enable == True:
			code = libCAENDigitizer.CAEN_DGTZ_EnableDRS4Correction(self._get_handle())
		else:
			code = libCAENDigitizer.CAEN_DGTZ_DisableDRS4Correction(self._get_handle())
		check_error_code(code)

def __init__():
	functions = [
		libCAENDigitizer.CAEN_DGTZ_OpenDigitizer,
		libCAENDigitizer.CAEN_DGTZ_CloseDigitizer,
		libCAENDigitizer.CAEN_DGTZ_Reset,
		libCAENDigitizer.CAEN_DGTZ_WriteRegister,
		libCAENDigitizer.CAEN_DGTZ_ReadRegister,
		libCAENDigitizer.CAEN_DGTZ_SetAcquisitionMode,
		libCAENDigitizer.CAEN_DGTZ_GetInfo,
		libCAENDigitizer.CAEN_DGTZ_AllocateEvent,
		libCAENDigitizer.CAEN_DGTZ_MallocReadoutBuffer,
		libCAENDigitizer.CAEN_DGTZ_FreeEvent,
		libCAENDigitizer.CAEN_DGTZ_FreeReadoutBuffer,
		libCAENDigitizer.CAEN_DGTZ_SetMaxNumEventsBLT,
		libCAENDigitizer.CAEN_DGTZ_SetFastTriggerMode,
		libCAENDigitizer.CAEN_DGTZ_SetFastTriggerDigitizing,
		libCAENDigitizer.CAEN_DGTZ_SetGroupFastTriggerDCOffset,
		libCAENDigitizer.CAEN_DGTZ_SetGroupFastTriggerThreshold,
		libCAENDigitizer.CAEN_DGTZ_SetPostTriggerSize,
		libCAENDigitizer.CAEN_DGTZ_SetRecordLength,
		libCAENDigitizer.CAEN_DGTZ_SetExtTriggerInputMode,
		libCAENDigitizer.CAEN_DGTZ_SetTriggerPolarity,
		libCAENDigitizer.CAEN_DGTZ_SendSWtrigger,
		libCAENDigitizer.CAEN_DGTZ_SetDRS4SamplingFrequency,
		libCAENDigitizer.CAEN_DGTZ_SetGroupEnableMask,
		libCAENDigitizer.CAEN_DGTZ_SetChannelDCOffset,
		libCAENDigitizer.CAEN_DGTZ_GetChannelDCOffset,
		libCAENDigitizer.CAEN_DGTZ_SWStartAcquisition,
		libCAENDigitizer.CAEN_DGTZ_SWStopAcquisition,
		libCAENDigitizer.CAEN_DGTZ_ReadData,
		libCAENDigitizer.CAEN_DGTZ_GetNumEvents,
		libCAENDigitizer.CAEN_DGTZ_GetEventInfo,
		libCAENDigitizer.CAEN_DGTZ_DecodeEvent,
		libCAENDigitizer.CAEN_DGTZ_LoadDRS4CorrectionData,
		libCAENDigitizer.CAEN_DGTZ_EnableDRS4Correction
	]
	for f in functions: # All digitizer functions return a long, indicating the operation outcome. Make ctypes be aware of that.
		f.restype = c_long