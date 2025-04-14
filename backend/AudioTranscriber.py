# import pyaudio
from re import A
import numpy as np
# import wave
from openai import audio
import torch
import whisper
import time
from tqdm import tqdm

RATE = 16000
CHANNELS = 1
CHUNK = 1024  # Set maximum duration to 30 seconds for the countdown
SILENCE_LIMIT = 60  # Number of consecutive silent chunks to stop recording

class AudioTranscriber:
    def __init__(self, accelerator, rate=RATE, channels=CHANNELS, chunk=CHUNK, model_size='medium'):
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

# from accelerate import Accelerator
# # Initialize the accelerator
# accelerator = Accelerator()
# # Initialize the AudioTranscriber with the accelerator

# audio_transcriber = AudioTranscriber(accelerator=accelerator)  # Replace with your accelerator if needed
# # Example usage 

# audio_file = r"uploads\audio_file.wav"  # Replace with your audio file path

# # Start timing
# start_time = time.time()

# result = audio_transcriber.transcribe_audio(audio_file)

# # End timing and calculate elapsed time
# end_time = time.time()
# elapsed_time = end_time - start_time

# print(f"Transcription result: {result}")
# print(f"Time taken for transcription: {elapsed_time:.2f} seconds")

