# import pyaudio
import numpy as np
# import wave
import torch
import whisper
import time
from tqdm import tqdm

RATE = 16000
CHANNELS = 1
CHUNK = 1024  # Set maximum duration to 30 seconds for the countdown
SILENCE_LIMIT = 60  # Number of consecutive silent chunks to stop recording

class AudioTranscriber:
    def __init__(self, accelerator, rate=RATE, channels=CHANNELS, chunk=CHUNK, model_size='turbo'):
        self.rate = rate
        self.channels = channels
        self.chunk = chunk
        # self.p = pyaudio.PyAudio()
        self.model = whisper.load_model(model_size, download_root='~/.cache/whisper').to(torch.float32)
        self.model = accelerator.prepare(self.model)

    # def save_audio(self, audio_data, filename="audio_input.wav"):
    #     with wave.open(filename, 'wb') as wf:
    #         wf.setnchannels(self.channels)
    #         wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
    #         wf.setframerate(self.rate)
    #         wf.writeframes(audio_data if isinstance(audio_data, bytes) else audio_data.tobytes())
    #     return filename
    
    def transcribe_audio(self, filename):
        result = self.model.transcribe(filename, language='pt')
        return result["text"]

    # def close(self):
    #     self.p.terminate()