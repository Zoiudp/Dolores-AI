from multiprocessing.pool import ThreadPool
import time
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from git import Tree
from openai import audio
from ray import get
import requests
from Inference import query_ollama_with_memory
from utils import text_to_speech
from accelerate import Accelerator
import os
import tempfile
import threading
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
import torch
from AudioTranscriber import AudioTranscriber
import ssl
import socket
#from sentimentanalysis import analyze_sentiment

accelerator = Accelerator()
app = Flask(__name__)
CORS(app)
app.debug = True
# Thread pool executor for managing threads
executor = ThreadPoolExecutor(max_workers=20)
# Global variable to track the listening state
is_listening = True

# Function to check initial listening state from frontend
# def check_initial_listening_state():
#     global is_listening
#     try:
#         # Make request to frontend (assuming it's running on port 3000)
#         response = requests.get('http://localhost:3000/api/listening-state')
#         if response.status_code == 200:
#             is_listening = response.json().get('isListening', True)
#     except:
#         # If frontend is not available, keep default value
#         pass

# # Check listening state when app starts
# check_initial_listening_state()

@app.route('/model_output/<filename>', methods=['GET'])
def get_audio(filename):
    try:
        audio_path = os.path.join(os.getcwd(), 'model_output', filename)
        return send_file(audio_path, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'message': 'File not found'}), 404


@app.route('/audio_image', methods=['POST'])	
def process_data():
    print("Requisição recebida")

    if 'audio' not in request.files or 'image' not in request.files:
        return jsonify({'message': 'No audio or image file part in the request'}), 400

    audio_file = request.files['audio']
    image_file = request.files['image']

    if audio_file.filename == '' or image_file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    audio_path = os.path.join('uploads', 'audio_file.wav')
    image_path = os.path.join('uploads', 'image_file.png')

    if audio_file and image_file:
        audio_file.save(audio_path)
        image_file.save(image_path)
    else:
        return jsonify({'message': 'Failed to upload audio or image file'}), 400

    torch.cuda.empty_cache()
    gc.collect()
    torch.cuda.reset_max_memory_allocated()

    start_time = time.time()

    global is_listening
    if not is_listening:
        return jsonify({'message': 'Listening is disabled, no audio will be fetched.'}), 400
    

    try:
        print('transcrevendo áudio...')
        transcriber = AudioTranscriber(accelerator)
        transcription_future = executor.submit(transcriber.transcribe_audio, audio_path)
        transcription = transcription_future.result()
        
        print('transcrição concluída')
        print(transcription)
        
        torch.cuda.empty_cache()
        gc.collect()
        torch.cuda.reset_max_memory_allocated()

        print('gerando inferencia...')
        inference_future = executor.submit(query_ollama_with_memory, transcription, image_path)
        # analise de sentimento
        #sentiment_future = executor.submit(analyze_sentiment, transcription)
        #sentiment = sentiment_future.result()
        #print('análise de sentimento concluída')

        inference_response = inference_future.result()
        
        torch.cuda.empty_cache()
        gc.collect()
        torch.cuda.reset_max_memory_allocated()
        
        print('gerando áudio...')
        tts_future = executor.submit(text_to_speech, inference_response)
        tts_future.result()

        torch.cuda.empty_cache()
        gc.collect()
        torch.cuda.reset_max_memory_allocated()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    end_time = time.time()
    exec_time = end_time - start_time

    return jsonify({
        'message': inference_response,
        #'sentiment': sentiment,
        'audio_source': f"https://192.158.1.5:5000/model_output/output.mp3",
        'tempo de execução': exec_time
    }), 200


@app.route('/set_listening_state', methods=['POST'])
def set_listening_state():
    global is_listening
    try:
        data = request.get_json()
        is_listening = data.get('isListening', True)
        return jsonify({'message': f'Listening state set to {is_listening}'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400


if __name__ == '__main__':
    cert_file = 'localhost.pem'
    key_file = 'localhost-key.pem'
    app.run(host="0.0.0.0", port=5000, ssl_context=(cert_file, key_file))