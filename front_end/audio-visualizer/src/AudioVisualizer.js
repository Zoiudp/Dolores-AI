import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const AMPLIFICATION_FACTOR = 2;

const AudioImageUploader = () => {
  const [audioFile, setAudioFile] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [status, setStatus] = useState('idle'); // 'idle', 'recording', 'processing', 'completed', 'error'
  const [audioUrl, setAudioUrl] = useState(null);

  const [soundWave, setSoundWave] = useState(Array(50).fill(0));
  const [averageAmplitude, setAverageAmplitude] = useState(0);
  const videoTrackRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioRef = useRef(null);
  const analyserRef = useRef(null);
  const dataArrayRef = useRef(null);
  const audioContextRef = useRef(null);

  // Start video stream for image capture (hidden)
  useEffect(() => {
    const startVideoStream = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        videoTrackRef.current = stream.getVideoTracks()[0];
      } catch (err) {
        console.error('Erro ao acessar a câmera:', err);
        setStatus('error');
      }
    };

    startVideoStream();
    return () => {
      if (videoTrackRef.current) {
        videoTrackRef.current.stop();
      }
    };
  }, []);

  // Função para capturar a imagem diretamente da câmera
  const captureImageFromCamera = async () => {
    if (!videoTrackRef.current) {
      console.error('Câmera não está disponível.');
      setStatus('error');
      return;
    }

    try {
      const imageCapture = new ImageCapture(videoTrackRef.current);
      const blob = await imageCapture.takePhoto();
      setImageFile(blob); // Define a imagem capturada
    } catch (err) {
      console.error('Erro ao capturar imagem da câmera:', err);
      setStatus('error');
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      analyserRef.current = analyser;
      dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount);
      audioContextRef.current = audioContext;

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioFile(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      setStatus('recording');
      mediaRecorder.start();
    } catch (err) {
      console.error('Error starting audio recording:', err);
      setStatus('error');
    }
  };

  const updateWaveform = () => {
    if ((status !== 'recording' && status !== 'completed') || !analyserRef.current || !dataArrayRef.current) return;

    analyserRef.current.getByteTimeDomainData(dataArrayRef.current);

    const amplitudes = Array.from(dataArrayRef.current).map(
      value => Math.abs(value - 128) * AMPLIFICATION_FACTOR
    );
    const average = amplitudes.reduce((a, b) => a + b, 0) / amplitudes.length;

    setSoundWave(amplitudes.slice(0, 50));
    setAverageAmplitude(average);
  };

  useEffect(() => {
    if (status === 'completed' && audioUrl && audioRef.current) {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaElementSource(audioRef.current);
      const analyser = audioContext.createAnalyser();
      source.connect(analyser);
      analyser.connect(audioContext.destination);

      analyserRef.current = analyser;
      dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount);
      audioContextRef.current = audioContext;

      const updateWaveformFromAudio = () => {
        updateWaveform();
        requestAnimationFrame(updateWaveformFromAudio);
      };

      updateWaveformFromAudio();
    }
  }, [status, audioUrl]);

  useEffect(() => {
    let animationId;
    if (status === 'recording' || status === 'completed') {
      const animate = () => {
        updateWaveform();
        animationId = requestAnimationFrame(animate);
      };
      animate();
    }
    return () => cancelAnimationFrame(animationId);
  }, [status]);

  useEffect(() => {
    let silenceCount = 0;

    const checkSilence = () => {
      if (status !== 'recording') return;

      if (averageAmplitude < 4) {
        silenceCount += 1;
      } else {
        silenceCount = 0;
      }

      if (silenceCount > 700) {
        stopRecording();
      }
    };

    let silenceIntervalId;
    if (status === 'recording') {
      silenceIntervalId = setInterval(checkSilence, 50);
    }

    return () => {
      clearInterval(silenceIntervalId);
    };
  }, [status, averageAmplitude]);

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setStatus('processing');

      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }

      // Trigger upload after a short delay to ensure everything is ready
      setTimeout(startProcess, 500);
    } else {
      console.error('MediaRecorder is not initialized.');
      setStatus('error');
    }
  };

  const uploadData = async () => {
    if (!audioFile) {
      setStatus('error');
      return;
    }

    const formData = new FormData();
    formData.append('audio', audioFile, 'recording.wav');

    if (imageFile) {
      formData.append('image', imageFile, 'snapshot.png');
    }

    try {

      const endpoint = 'https://192.168.1.8:5000/audio_image';
      const baseUrl = 'https://192.168.1.8:5000';
      const response = await axios.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const audioResponse = await axios.get(`${baseUrl}/model_output/output.mp3`, {
        responseType: 'blob'
      });

      const processedAudioUrl = URL.createObjectURL(audioResponse.data);
      setAudioUrl(processedAudioUrl);
      setStatus('completed');
    } catch (err) {
      console.error('Error uploading data:', err);
      setStatus('error');
    }
  };

  const startProcess = async () => {
    setStatus('processing');
    await captureImageFromCamera();
    await uploadData();
  };

  const resetRecording = () => {
    setStatus('idle');
    setAudioUrl(null);
    setSoundWave(Array(50).fill(0));
  };

  // Status messages and colors
  const statusInfo = {
    'idle': { 
      message: 'Press Record to Start', 
      color: 'bg-amber-500/30 border-amber-500/50 animate-pulse' 
    },
    'recording': { 
      message: 'Recording...', 
      color: 'bg-red-500/30 border-red-500/50 animate-pulse' 
    },
    'processing': { 
      message: 'Processing...', 
      color: 'bg-blue-500/30 border-blue-500/50 animate-pulse' 
    },
    'completed': { 
      message: 'Completed!', 
      color: 'bg-green-500/30 border-green-500/50 animate-pulse' 
    },
    'error': { 
      message: 'Error Occurred', 
      color: 'bg-red-700/30 border-red-700/50' 
    }
  };

  return (
    <div className="relative min-h-screen bg-black flex items-center justify-center">
      <div className="relative max-w-2xl w-full">
        <div className="relative rounded-lg overflow-hidden">
          <div className={`relative aspect-square transition-all duration-300 
            ${statusInfo[status].color}`}>
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full px-12">
              <div className="flex items-center justify-center h-32 gap-1">
                {soundWave.map((height, index) => (
                  <div
                    key={index}
                    className="w-1 bg-amber-500"
                    style={{
                      height: `${Math.min(height, 100)}%`,
                      opacity: 0.5 + Math.min(height, 100) / 100,
                      transition: 'all 0.1s ease',
                    }}
                  />
                ))}
              </div>
              <div className="text-center text-white mt-4 text-xl">
                {statusInfo[status].message}
              </div>
            </div>

            <div className="absolute inset-2 border-4 rounded-full" />
            <div className="absolute inset-6 border-2 rounded-full" />
          </div>
        </div>

        <div className="mt-4 flex justify-center space-x-4">
          {status === 'idle' && (
            <button 
              onClick={startRecording}
              className="px-6 py-3 bg-amber-500 text-black rounded-full hover:bg-amber-600 transition-colors"
            >
              Start Recording
            </button>
          )}

          {status === 'recording' && (
            <button 
              onClick={stopRecording}
              className="px-6 py-3 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
            >
              Stop Recording
            </button>
          )}

          {status === 'completed' && (
            <div className="flex space-x-4">
              {audioUrl && (
                <audio ref={audioRef} src={audioUrl} controls autoPlay 
                  onEnded={startRecording} 
                  className="w-full"
                />
              )}
              <button 
                onClick={resetRecording}
                className="px-6 py-3 bg-green-500 text-white rounded-full hover:bg-green-600 transition-colors"
              >
                playing the audio
              </button>
            </div>
          )}

          {status === 'error' && (
            <button 
              onClick={resetRecording}
              className="px-6 py-3 bg-red-700 text-white rounded-full hover:bg-red-800 transition-colors"
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AudioImageUploader;