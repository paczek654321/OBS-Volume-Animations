import obspython as obs, numpy as np, pyaudio, math

UPDATE_FREQUENCY = 50
VOLUME_GATE = -40
GRACE_PERIOD = 5
TALKING_ITEM_NAME = "name"
SILENT_ITEM_NAME = "name"

def script_properties():
	settings = obs.obs_properties_create()

	obs.obs_properties_add_int(settings, "update_frequency", "Update Frequency (ms)", 10, 1000, 10)
	obs.obs_properties_add_float_slider(settings, "volume_gate", "Volume Gate (dB)", -90.0, 0.0, 1.0)
	obs.obs_properties_add_int(settings, "grace_period_ms", "Grace Period (ms)", 0, 10000, 10)
	obs.obs_properties_add_text(settings, "talking_item_name", "Talking Item Name", obs.OBS_TEXT_DEFAULT)
	obs.obs_properties_add_text(settings, "silent_item_name", "Silent Item Name", obs.OBS_TEXT_DEFAULT)

	return settings

def script_defaults(settings):
	obs.obs_data_set_default_int(settings, "update_frequency", UPDATE_FREQUENCY)
	obs.obs_data_set_default_double(settings, "volume_gate", VOLUME_GATE)
	obs.obs_data_set_default_int(settings, "grace_period_ms", GRACE_PERIOD*UPDATE_FREQUENCY)
	obs.obs_data_set_default_string(settings, "talking_item_name", TALKING_ITEM_NAME)
	obs.obs_data_set_default_string(settings, "silent_item_name", SILENT_ITEM_NAME)

def script_update(settings):
	global UPDATE_FREQUENCY, VOLUME_GATE, GRACE_PERIOD_MS, GRACE_PERIOD, TALKING_ITEM_NAME, SILENT_ITEM_NAME

	if (UPDATE_FREQUENCY != obs.obs_data_get_int(settings, "update_frequency")):
		UPDATE_FREQUENCY = obs.obs_data_get_int(settings, "update_frequency")
		obs.timer_remove(update)
		obs.timer_add(update, UPDATE_FREQUENCY)

	VOLUME_GATE = obs.obs_data_get_double(settings, "volume_gate")
	GRACE_PERIOD = math.ceil(obs.obs_data_get_int(settings, "grace_period_ms")/UPDATE_FREQUENCY)
	TALKING_ITEM_NAME = obs.obs_data_get_string(settings, "talking_item_name")
	SILENT_ITEM_NAME = obs.obs_data_get_string(settings, "silent_item_name")

class AudioManager():
	def __init__(self):
		self.pyAudio = pyaudio.PyAudio()

		device = self.get_default_device()
		self.stream = self.pyAudio.open(format=pyaudio.paInt16, channels=1, rate=math.floor(device["defaultSampleRate"]), input=True, frames_per_buffer=1024, input_device_index=device["index"])
	
	def unload(self):
		self.stream.stop_stream()
		self.stream.close()
		self.pyAudio.terminate()

	def get_default_device(self):
		for i in range(self.pyAudio.get_device_count()):
			info = self.pyAudio.get_device_info_by_index(i)
			if (("Microsoft" in info["name"] and "- Input" in info["name"]) or (info["name"] == "pipewire")):
				return info
	
	def get_volume(self):
		data = np.frombuffer(self.stream.read(self.stream._frames_per_buffer, exception_on_overflow=False), dtype=np.int16)
		data = data.astype(np.float32)
		volume = np.sqrt(np.mean(data**2))
		if volume == 0: return -math.inf
		return 20 * np.log10(volume/32768)

audioManager = AudioManager()

talking = 0
def update():
	global talking
	if (audioManager.get_volume() > VOLUME_GATE):
		if (talking < GRACE_PERIOD): set_state(True)
		talking = GRACE_PERIOD
	else:
		if (talking == 0): set_state(False)
		talking -= 1

def set_state(state):
	scene_source = obs.obs_frontend_get_current_scene()
	current_scene = obs.obs_scene_from_source(scene_source)

	obs.obs_sceneitem_set_visible(obs.obs_scene_find_source_recursive(current_scene, TALKING_ITEM_NAME), state)
	obs.obs_sceneitem_set_visible(obs.obs_scene_find_source_recursive(current_scene, SILENT_ITEM_NAME), not state)

	obs.obs_source_release(scene_source)

def script_description(): return "<h1>Volume animations</h1>A script to animate your scene based on mic input"

def script_load(settings): obs.timer_add(update, UPDATE_FREQUENCY)

def script_unload(): audioManager.unload()