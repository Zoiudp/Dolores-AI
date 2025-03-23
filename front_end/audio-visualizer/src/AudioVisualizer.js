import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const AMPLIFICATION_FACTOR = 2;
const LISTENING_TRIGGER_MULTIPLIER = 1.5; // Para disparar a gravação a partir do estado "listening"
const RECORDING_THRESHOLD_MULTIPLIER = 1.4; // Para validar o áudio durante a gravação
const SILENCE_THRESHOLD = 40; // Amplitude below this is considered silence
const MAX_SILENCE_DURATION = 1500; // Maximum silence duration in ms before stopping (1.5 seconds)
const SILENCE_CHECK_INTERVAL = 150; // Check for silence every 150ms
const ERROR_RECOVERY_DELAY = 1500; // Delay before recovering from error state (1.5 seconds)

const AudioImageUploader = () => {
  // Estados para controlar o fluxo:
  // 'calibrating' (calibração), 'listening' (aguardando entrada), 'recording', 'processing', 'completed', 'error'
  const [status, setStatus] = useState('calibrating');
  const [audioFile, setAudioFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [soundWave, setSoundWave] = useState(Array(50).fill(0));
  const [averageAmplitude, setAverageAmplitude] = useState(0);
  const [ambientBaseline, setAmbientBaseline] = useState(0);
  
  // States for LED face
  const [emotion, setEmotion] = useState('neutral');
  
  // Silence tracking state
  const [silenceDuration, setSilenceDuration] = useState(0);
  const [isSilent, setIsSilent] = useState(false);
  const lastSoundTimeRef = useRef(Date.now());

  const videoRef = useRef(null);
  const videoTrackRef = useRef(null);
  const audioStreamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioRef = useRef(null);
  const analyserRef = useRef(null);
  const dataArrayRef = useRef(null);
  const audioContextRef = useRef(null);
  const calibrationSamplesRef = useRef([]);
  // Ref para indicar se durante a gravação houve entradas com amplitude acima do threshold
  const recordingValidRef = useRef(false);

  // Inicia o stream de vídeo para captura da imagem (e exibição)
  useEffect(() => {
    const startVideoStream = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        videoTrackRef.current = stream.getVideoTracks()[0];
        
        // Display video feed
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
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

  // Configura o stream de áudio, AudioContext e Analyser assim que o componente é montado
  useEffect(() => {
    const setupAudio = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioStreamRef.current = stream;
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);

        analyserRef.current = analyser;
        dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount);
        audioContextRef.current = audioContext;

        // Inicia em modo de calibração
        setStatus('calibrating');
      } catch (err) {
        console.error('Erro ao acessar o microfone:', err);
        setStatus('error');
      }
    };

    setupAudio();
    return () => {
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  // Set LED face emotion based on status
  useEffect(() => {
    switch (status) {
      case 'calibrating':
        setEmotion('thinking');
        break;
      case 'listening':
        setEmotion('neutral');
        break;
      case 'recording':
        setEmotion('happy');
        break;
      case 'processing':
        setEmotion('processing');
        break;
      case 'completed':
        setEmotion('excited');
        break;
      case 'error':
        setEmotion('sad');
        break;
      default:
        setEmotion('neutral');
    }
  }, [status]);

  // Handle error state - wait 1.5 seconds then return to listening state
  useEffect(() => {
    if (status === 'error') {
      const errorTimer = setTimeout(() => {
        console.log('Recovering from error state...');
        setStatus('listening');
      }, ERROR_RECOVERY_DELAY);
      
      return () => clearTimeout(errorTimer);
    }
  }, [status]);

  // Função para capturar a imagem da câmera
  const captureImageFromCamera = async () => {
    if (!videoTrackRef.current) {
      console.error('Câmera não está disponível.');
      setStatus('error');
      return;
    }
    try {
      const imageCapture = new ImageCapture(videoTrackRef.current);
      const blob = await imageCapture.takePhoto();
      return blob;
    } catch (err) {
      console.error('Erro ao capturar imagem da câmera:', err);
      setStatus('error');
    }
  };

  // Atualiza o waveform e calcula a amplitude média
  const updateWaveform = () => {
    if (!analyserRef.current || !dataArrayRef.current) return;
    analyserRef.current.getByteTimeDomainData(dataArrayRef.current);

    const amplitudes = Array.from(dataArrayRef.current).map(
      value => Math.abs(value - 128) * AMPLIFICATION_FACTOR
    );
    const average = amplitudes.reduce((a, b) => a + b, 0) / amplitudes.length;

    setSoundWave(amplitudes.slice(0, 50));
    setAverageAmplitude(average);

    // Update silence detection
    const currentTime = Date.now();
    const isCurrentlySilent = average < SILENCE_THRESHOLD;
    
    if (status === 'recording') {
      // If we detect sound, update the last sound time
      if (!isCurrentlySilent) {
        lastSoundTimeRef.current = currentTime;
        if (average > ambientBaseline * RECORDING_THRESHOLD_MULTIPLIER) {
          recordingValidRef.current = true; // Mark that we got valid audio
        }
      }
      
      // Calculate how long we've been silent
      const currentSilenceDuration = isCurrentlySilent ? currentTime - lastSoundTimeRef.current : 0;
      setSilenceDuration(currentSilenceDuration);
      setIsSilent(isCurrentlySilent);

      if (isCurrentlySilent && currentSilenceDuration > MAX_SILENCE_DURATION) {
        stopRecording();
      }
    }

    if (status === 'calibrating') {
      calibrationSamplesRef.current.push(average);
    } else if (status === 'listening' && ambientBaseline > 0) {
      if (average > ambientBaseline * LISTENING_TRIGGER_MULTIPLIER) {
        startRecording();
      }
    }
  };

  // Loop de animação para atualização contínua do waveform
  useEffect(() => {
    let animationId;
    const animate = () => {
      updateWaveform();
      animationId = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(animationId);
  }, [status, ambientBaseline]);

  // Efeito para a calibração: após 3 segundos, calcula a média dos ruídos ambiente
  useEffect(() => {
    if (status === 'calibrating') {
      const timer = setTimeout(() => {
        const samples = calibrationSamplesRef.current;
        if (samples.length > 0) {
          const baseline = samples.reduce((a, b) => a + b, 0) / samples.length;
          setAmbientBaseline(baseline);
        }
        calibrationSamplesRef.current = [];
        setStatus('listening');
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [status]);

  // Enhanced silence detection during recording
  useEffect(() => {
    if (status !== 'recording') return;
    
    // Check if silence has exceeded the maximum allowed duration
    const silenceTimer = setInterval(() => {
      if (isSilent && silenceDuration > MAX_SILENCE_DURATION) {
        console.log(`Stopping recording due to silence: ${silenceDuration}ms`);
        stopRecording();
      }
    }, SILENCE_CHECK_INTERVAL);
    
    return () => clearInterval(silenceTimer);
  }, [status, isSilent, silenceDuration]);

  // Inicia a gravação utilizando o stream já configurado
  const startRecording = () => {
    if (status !== 'listening') return; // Garante que a gravação só inicie a partir do estado "listening"
    setStatus('recording');
    recordingValidRef.current = false; // Reinicia a flag de validação
    lastSoundTimeRef.current = Date.now(); // Reset the last sound time
    setSilenceDuration(0);
    setIsSilent(false);
    
    try {
      const mediaRecorder = new MediaRecorder(audioStreamRef.current);
      audioChunksRef.current = [];
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = () => {
        // Se não houve áudio acima do threshold durante a gravação, descarta e retorna ao estado "listening"
        if (!recordingValidRef.current) {
          resetRecording();
        } else {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
          setAudioFile(audioBlob);
          setStatus('processing');
          setTimeout(startProcess, 500);
        }
      };

      mediaRecorder.start();
    } catch (err) {
      console.error('Erro ao iniciar a gravação:', err);
      setStatus('error');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      // A validação é feita no callback onstop do MediaRecorder
    } else {
      console.error('MediaRecorder não está inicializado.');
      setStatus('error');
    }
  };

  // Realiza o upload dos dados: áudio e imagem capturada
  const uploadData = async () => {
    if (!audioFile) {
      setStatus('error');
      return;
    }

    const formData = new FormData();
    formData.append('audio', audioFile, 'recording.wav');

    const imageBlob = await captureImageFromCamera();
    if (imageBlob) {
      formData.append('image', imageBlob, 'snapshot.png');
    }

    try {
      const endpoint = 'https://192.168.1.7:5000/audio_image';
      const baseUrl = 'https://192.168.1.7:5000';
      await axios.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const audioResponse = await axios.get(`${baseUrl}/model_output/output.mp3`, {
        responseType: 'blob'
      });
      const processedAudioUrl = URL.createObjectURL(audioResponse.data);
      setAudioUrl(processedAudioUrl);
      setStatus('completed');
      
      // Now we'll play the audio programmatically to ensure we can track when it completes
      if (audioRef.current) {
        audioRef.current.src = processedAudioUrl;
        audioRef.current.play();
      }
    } catch (err) {
      console.error('Erro ao enviar os dados:', err);
      setStatus('error');
    }
  };

  // Inicia o processo de upload após a gravação validada
  const startProcess = async () => {
    await uploadData();
  };

  // Reset recording state and prepare for next interaction
  const resetRecording = () => {
    setAudioFile(null);
    setAudioUrl(null);
    setSoundWave(Array(50).fill(0));
    setStatus('listening');
    setSilenceDuration(0);
    setIsSilent(false);
  };

  // Handle audio ended event - this is the key modification to wait for audio completion
  useEffect(() => {
    if (audioRef.current) {
      // Add event listener to audioRef
      const handleAudioEnded = () => {
        console.log("Audio playback completed, returning to listening state");
        resetRecording();
      };
      
      audioRef.current.addEventListener('ended', handleAudioEnded);
      
      // Clean up
      return () => {
        if (audioRef.current) {
          audioRef.current.removeEventListener('ended', handleAudioEnded);
        }
      };
    }
  }, [audioRef.current]); // Dependencies array includes audioRef.current to ensure it gets recreated when needed

  // Remove the old timer-based reset and keep audio in completed state until it finishes playing
  useEffect(() => {
    if (status === 'completed' && audioUrl && audioRef.current) {
      // We'll let the 'ended' event listener handle the transition back to listening
      // No timeout needed anymore
    }
  }, [status, audioUrl]);

  // Mensagens e cores para cada estado
  const statusInfo = {
    calibrating: { 
      message: 'Calibrando ruídos ambiente...', 
      color: 'bg-blue-500/30 border-blue-500/50 animate-pulse' 
    },
    listening: { 
      message: 'Aguardando entrada de áudio...', 
      color: 'bg-amber-500/30 border-amber-500/50 animate-pulse' 
    },
    recording: { 
      message: `Gravando${isSilent ? ' (Silêncio detectado)' : ''}...`, 
      color: 'bg-red-500/30 border-red-500/50 animate-pulse' 
    },
    processing: { 
      message: 'Processando...', 
      color: 'bg-blue-500/30 border-blue-500/50 animate-pulse' 
    },
    completed: { 
      message: 'Concluído! Reproduzindo resposta...', 
      color: 'bg-green-500/30 border-green-500/50 animate-pulse' 
    },
    error: { 
      message: 'Erro detectado. Recuperando...', 
      color: 'bg-red-700/30 border-red-700/50 animate-pulse' 
    }
  };

  // LED Face component
  const LEDFace = ({ emotion }) => {
    // Eyes styles based on emotion
    const getEyeStyle = () => {
      switch (emotion) {
        case 'happy':
          return { transform: 'scaleY(0.7) translateY(-5px)', borderRadius: '50% 50% 0 0' };
        case 'sad':
          return { transform: 'scaleY(0.7) translateY(5px)', borderRadius: '0 0 50% 50%' };
        case 'excited':
          return { transform: 'scale(1.2)', borderRadius: '50%' };
        case 'thinking':
          return { transform: 'scaleY(0.5)', borderRadius: '50%' };
        case 'processing':
          return { transform: 'scaleY(0.3) scaleX(1.2)', animation: 'blink 1s infinite' };
        default:
          return { borderRadius: '50%' };
      }
    };

    // Mouth styles based on emotion
    const getMouthStyle = () => {
      switch (emotion) {
        case 'happy':
          return { borderRadius: '0 0 100px 100px', height: '50px', width: '120px' };
        case 'sad':
          return { borderRadius: '100px 100px 0 0', height: '50px', width: '120px', transform: 'translateY(20px)' };
        case 'excited':
          return { borderRadius: '0 0 100px 100px', height: '70px', width: '140px' };
        case 'thinking':
          return { width: '60px', height: '10px', transform: 'translateY(20px)' };
        case 'processing':
          return { width: '40px', height: '40px', borderRadius: '50%', animation: 'pulse 1.5s infinite' };
        default:
          return { width: '80px', height: '15px' };
      }
    };

    return (
      <div className="led-face flex flex-col items-center justify-center bg-gray-900 p-4 rounded-lg w-full h-full">
        <div className="eyes flex justify-between w-3/4 mb-12">
          <div 
            className="eye bg-green-500" 
            style={{
              width: '80px',
              height: '80px',
              ...getEyeStyle()
            }}
          />
          <div 
            className="eye bg-green-500" 
            style={{
              width: '80px',
              height: '80px',
              ...getEyeStyle()
            }}
          />
        </div>
        <div 
          className="mouth bg-green-500"
          style={getMouthStyle()}
        />
      </div>
    );
  };

  return (
    <div className="relative min-h-screen bg-black flex items-center justify-center p-6">
      <div className="grid grid-cols-2 gap-6 w-full max-w-6xl">
        {/* Left side - LED Face */}
        <div className="flex flex-col h-full">
          <div className="bg-gray-800 rounded-lg overflow-hidden flex-grow">
            <LEDFace emotion={emotion} />
          </div>
          <div className="mt-4 text-center text-white text-xl">
            {statusInfo[status].message}
          </div>
          {status === 'recording' && isSilent && (
            <div className="text-center text-amber-300 mt-2">
              Silêncio: {Math.round(silenceDuration / 100) / 10}s
            </div>
          )}
        </div>

        {/* Right side - Camera and Waveform */}
        <div className="flex flex-col">
          {/* Camera feed */}
          <div className="relative bg-gray-800 rounded-lg overflow-hidden aspect-video">
            <video 
              ref={videoRef} 
              autoPlay 
              playsInline 
              muted 
              className="w-full h-full object-cover"
            />
          </div>
          
          {/* Audio waveform */}
          <div className="mt-4 bg-gray-800 rounded-lg p-4 h-32">
            <div className="flex items-center justify-center h-full gap-1">
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
          </div>
          
          {/* Audio player (when completed) */}
          {status === 'completed' && audioUrl && (
            <audio
              ref={audioRef}
              src={audioUrl}
              controls
              autoPlay
              className="w-full mt-4"
            />
          )}
        </div>
      </div>
      
      {/* CSS Animations */}
      <style jsx>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.2); }
        }
      `}</style>
    </div>
  );
};

export default AudioImageUploader;