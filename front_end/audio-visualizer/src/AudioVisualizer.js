import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

// Configuration settings grouped by functionality
const CONFIG = {
  audio: {
    amplificationFactor: 2,
    listeningTriggerMultiplier: 1.5,
    recordingThresholdMultiplier: 1.4,
    baseSilenceThreshold: 40,
    silenceThresholdRatio: 1.2,
    minSilenceThreshold: 15,
    hysteresisFactor: 0.8,
    frequencyAnalysisEnabled: true
  },
  timing: {
    maxSilenceDuration: 2500,        // 2.5 seconds for natural pauses detection
    silenceCheckInterval: 500,       // Check interval for silence
    errorRecoveryDelay: 1500,        // Delay before recovering from errors
    calibrationDuration: 500,       // Initial calibration time
    rollingCalibrationWindow: 10000, // 10 second window for rolling calibration
    rollingCalibrationInterval: 1000,// Update calibration every second
    minValidRecordingDuration: 1000, // Minimum valid recording length
    resetDelayAfterPlayback: 1000    // Delay before reset after playback
  },
  api: {
    baseUrl: 'https://192.168.1.9:5000',
    audioImageEndpoint: '/audio_image',
    audioOutputPath: '/model_output/output.mp3'
  }
};

// Status messages and visual styles for each state
const STATUS_INFO = {
  calibrating: { 
    message: 'Calibrando ruídos ambiente...', 
    color: 'bg-blue-500/30 border-blue-500/50 animate-pulse',
    emotion: 'thinking'
  },
  listening: { 
    message: 'Aguardando entrada de áudio...', 
    color: 'bg-amber-500/30 border-amber-500/50 animate-pulse',
    emotion: 'neutral'
  },
  recording: { 
    message: 'Gravando...', 
    color: 'bg-red-500/30 border-red-500/50 animate-pulse',
    emotion: 'happy'
  },
  processing: { 
    message: 'Processando...', 
    color: 'bg-blue-500/30 border-blue-500/50 animate-pulse',
    emotion: 'processing'
  },
  completed: { 
    message: 'Concluído! Reproduzindo resposta...', 
    color: 'bg-green-500/30 border-green-500/50 animate-pulse',
    emotion: 'excited'
  },
  error: { 
    message: 'Erro detectado. Recuperando...', 
    color: 'bg-red-700/30 border-red-700/50 animate-pulse',
    emotion: 'sad'
  }
};

/**
 * LED Face component - displays animated face with different emotions
 */
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

const AudioImageUploader = () => {
  // ========================= STATE MANAGEMENT =========================
  // Primary application state
  const [status, setStatus] = useState('calibrating');
  const [audioFile, setAudioFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [soundWave, setSoundWave] = useState(Array(50).fill(0));
  
  // Audio processing state
  const [averageAmplitude, setAverageAmplitude] = useState(0);
  const [ambientBaseline, setAmbientBaseline] = useState(0);
  const [silenceThreshold, setSilenceThreshold] = useState(CONFIG.audio.baseSilenceThreshold);
  const [silenceDuration, setSilenceDuration] = useState(0);
  const [isSilent, setIsSilent] = useState(false);
  
  // Debug information
  const [debugCalibration, setDebugCalibration] = useState({
    baseline: 0,
    threshold: 0,
    currentLevel: 0
  });

  // ========================= REFS =========================
  // Media refs
  const videoRef = useRef(null);
  const videoTrackRef = useRef(null);
  const audioRef = useRef(null);
  const audioStreamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  
  // Audio processing refs
  const analyserRef = useRef(null);
  const timeDataRef = useRef(null);
  const frequencyDataRef = useRef(null);
  const audioContextRef = useRef(null);
  
  // State tracking refs
  const lastSoundTimeRef = useRef(Date.now());
  const calibrationSamplesRef = useRef([]);
  const rollingCalibrationSamplesRef = useRef([]);
  const recordingStartTimeRef = useRef(0);
  const recordingValidRef = useRef(false);
  const previousSilenceStateRef = useRef(false);
  
  // Flag refs for preventing race conditions
  const isProcessingRequestRef = useRef(false);
  const resetInProgressRef = useRef(false);

  // ========================= VIDEO STREAM SETUP =========================
  useEffect(() => {
    const startVideoStream = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        videoTrackRef.current = stream.getVideoTracks()[0];
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error('Error accessing camera:', err);
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

  // ========================= AUDIO STREAM SETUP =========================
  useEffect(() => {
    const setupAudio = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioStreamRef.current = stream;
        
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048; // Larger FFT size for better frequency resolution
        
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);

        analyserRef.current = analyser;
        timeDataRef.current = new Uint8Array(analyser.frequencyBinCount);
        frequencyDataRef.current = new Uint8Array(analyser.frequencyBinCount);
        audioContextRef.current = audioContext;

        setStatus('calibrating');
      } catch (err) {
        console.error('Error accessing microphone:', err);
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

  // ========================= ERROR HANDLING =========================
  useEffect(() => {
    if (status === 'error') {
      // Clear any in-progress requests
      isProcessingRequestRef.current = false;
      
      const errorTimer = setTimeout(() => {
        resetInProgressRef.current = false;
        setStatus('listening');
      }, CONFIG.timing.errorRecoveryDelay);
      
      return () => clearTimeout(errorTimer);
    }
  }, [status]);

  // ========================= AUDIO PLAYBACK HANDLER =========================
  useEffect(() => {
    if (audioRef.current) {
      const handleAudioEnded = () => {
        // Add a small delay after playback finishes
        setTimeout(() => {
          resetRecording();
        }, CONFIG.timing.resetDelayAfterPlayback);
      };
      
      audioRef.current.addEventListener('ended', handleAudioEnded);
      
      return () => {
        if (audioRef.current) {
          audioRef.current.removeEventListener('ended', handleAudioEnded);
        }
      };
    }
  }, [audioRef.current]);
  
  // ========================= INITIAL CALIBRATION =========================
  useEffect(() => {
    if (status === 'calibrating') {
      const timer = setTimeout(() => {
        const samples = calibrationSamplesRef.current;
        if (samples.length > 0) {
          // Calculate baseline using trimmed mean (removing outliers)
          const sortedSamples = [...samples].sort((a, b) => a - b);
          const trimAmount = Math.floor(sortedSamples.length * 0.1); // Trim 10% from each end
          const trimmedSamples = sortedSamples.slice(trimAmount, sortedSamples.length - trimAmount);
          
          const baseline = trimmedSamples.reduce((a, b) => a + b, 0) / trimmedSamples.length;
          setAmbientBaseline(baseline);
          
          // Set silence threshold based on baseline with a minimum floor
          const calculatedThreshold = Math.max(
            baseline * CONFIG.audio.silenceThresholdRatio,
            CONFIG.audio.minSilenceThreshold
          );
          setSilenceThreshold(calculatedThreshold);
          
          setDebugCalibration({
            baseline: baseline,
            threshold: calculatedThreshold,
            currentLevel: averageAmplitude
          });
        }
        
        calibrationSamplesRef.current = [];
        
        // Initialize rolling calibration with current values
        rollingCalibrationSamplesRef.current = Array(10).fill().map(() => ({
          timestamp: Date.now(),
          level: ambientBaseline || CONFIG.audio.baseSilenceThreshold / CONFIG.audio.silenceThresholdRatio
        }));
        
        // Clear flags before transitioning to listening state
        isProcessingRequestRef.current = false;
        resetInProgressRef.current = false;
        setStatus('listening');
      }, CONFIG.timing.calibrationDuration);
      
      return () => clearTimeout(timer);
    }
  }, [status, averageAmplitude]);

  // ========================= ROLLING CALIBRATION =========================
  useEffect(() => {
    if (status !== 'listening') return;
    
    const updateCalibration = () => {
      const samples = rollingCalibrationSamplesRef.current;
      if (samples.length < 5) return; // Need minimum samples for reliable calibration
      
      // Find the quietest periods (lowest 20% of samples)
      const sortedLevels = [...samples].sort((a, b) => a.level - b.level);
      const quietSamplesCount = Math.max(1, Math.floor(sortedLevels.length * 0.2));
      const quietSamples = sortedLevels.slice(0, quietSamplesCount);
      
      // Calculate new baseline from quiet periods
      const newBaseline = quietSamples.reduce((sum, sample) => sum + sample.level, 0) / quietSamples.length;
      
      // Gradually adjust the baseline (weighted average with current baseline)
      const adjustedBaseline = (ambientBaseline * 0.7) + (newBaseline * 0.3);
      
      // Update the baseline if it has changed significantly
      if (Math.abs(adjustedBaseline - ambientBaseline) > (ambientBaseline * 0.2)) {
        setAmbientBaseline(adjustedBaseline);
        
        // Recalculate silence threshold based on new baseline
        const newThreshold = Math.max(
          adjustedBaseline * CONFIG.audio.silenceThresholdRatio,
          CONFIG.audio.minSilenceThreshold
        );
        setSilenceThreshold(newThreshold);
        
        setDebugCalibration(prev => ({
          ...prev,
          baseline: adjustedBaseline,
          threshold: newThreshold
        }));
      }
    };
    
    const calibrationInterval = setInterval(updateCalibration, CONFIG.timing.rollingCalibrationInterval);
    return () => clearInterval(calibrationInterval);
  }, [status, ambientBaseline]);

  // ========================= AUDIO ANALYSIS FUNCTIONS =========================
  /**
   * Analyzes frequency characteristics for better silence detection
   */
  const calculateFrequencyCharacteristics = () => {
    if (!analyserRef.current || !frequencyDataRef.current) return 0;
    
    analyserRef.current.getByteFrequencyData(frequencyDataRef.current);
    
    const frequencies = Array.from(frequencyDataRef.current);
    
    // Focus on voice frequency range (approximately 85-255 Hz)
    const voiceRangeStart = Math.floor(85 * frequencyDataRef.current.length / audioContextRef.current.sampleRate);
    const voiceRangeEnd = Math.ceil(255 * frequencyDataRef.current.length / audioContextRef.current.sampleRate);
    
    const voiceFrequencies = frequencies.slice(voiceRangeStart, voiceRangeEnd + 1);
    
    // Calculate average energy in voice frequency range
    const voiceEnergy = voiceFrequencies.reduce((sum, value) => sum + value, 0) / voiceFrequencies.length;
    
    return voiceEnergy;
  };

  /**
   * Updates waveform visualization and detects sound/silence
   */
  const updateWaveform = () => {
    if (!analyserRef.current || !timeDataRef.current) return;
    
    // Get time domain data (waveform)
    analyserRef.current.getByteTimeDomainData(timeDataRef.current);
    
    // Calculate amplitude from time domain data
    const amplitudes = Array.from(timeDataRef.current).map(
      value => Math.abs(value - 128) * CONFIG.audio.amplificationFactor
    );
    const average = amplitudes.reduce((a, b) => a + b, 0) / amplitudes.length;

    // Get frequency domain energy if enabled
    let voiceEnergy = 0;
    if (CONFIG.audio.frequencyAnalysisEnabled) {
      voiceEnergy = calculateFrequencyCharacteristics();
    }
    
    // Combine time and frequency domain data for better detection
    const combinedSignalStrength = CONFIG.audio.frequencyAnalysisEnabled 
      ? (average * 0.7) + (voiceEnergy * 0.3) // Weighted combination
      : average;

    // Update state
    setSoundWave(amplitudes.slice(0, 50));
    setAverageAmplitude(combinedSignalStrength);

    // Update debug info
    setDebugCalibration(prev => ({
      ...prev,
      currentLevel: combinedSignalStrength
    }));

    // Rolling calibration samples - store data if we're in listening mode
    if (status === 'listening') {
      const now = Date.now();
      rollingCalibrationSamplesRef.current.push({
        timestamp: now,
        level: combinedSignalStrength
      });
      
      // Only keep samples within our rolling window
      rollingCalibrationSamplesRef.current = rollingCalibrationSamplesRef.current.filter(
        sample => (now - sample.timestamp) <= CONFIG.timing.rollingCalibrationWindow
      );
    }
    
    // Silence detection with hysteresis
    const currentTime = Date.now();
    
    // Apply hysteresis to prevent rapid switching
    let isCurrentlySilent;
    if (previousSilenceStateRef.current) {
      // If previously silent, require higher level to exit silence state
      isCurrentlySilent = combinedSignalStrength < (silenceThreshold / CONFIG.audio.hysteresisFactor);
    } else {
      // If previously not silent, use normal threshold to enter silence state
      isCurrentlySilent = combinedSignalStrength < silenceThreshold;
    }
    
    previousSilenceStateRef.current = isCurrentlySilent;
    
    // Handle different states
    if (status === 'recording') {
      // If we detect sound, update the last sound time
      if (!isCurrentlySilent) {
        lastSoundTimeRef.current = currentTime;
        if (combinedSignalStrength > ambientBaseline * CONFIG.audio.recordingThresholdMultiplier) {
          recordingValidRef.current = true; // Mark that we got valid audio
        }
      }
      
      // Calculate how long we've been silent
      const currentSilenceDuration = isCurrentlySilent ? currentTime - lastSoundTimeRef.current : 0;
      setSilenceDuration(currentSilenceDuration);
      setIsSilent(isCurrentlySilent);
      
      // Stop recording only if we've been silent for long enough AND we have a valid recording
      const recordingDuration = currentTime - recordingStartTimeRef.current;
      if (isCurrentlySilent && 
          currentSilenceDuration > CONFIG.timing.maxSilenceDuration && 
          recordingDuration > CONFIG.timing.minValidRecordingDuration &&
          recordingValidRef.current) {
        stopRecording();
      }
    }

    if (status === 'calibrating') {
      calibrationSamplesRef.current.push(combinedSignalStrength);
    } else if (status === 'listening' && ambientBaseline > 0) {
      // Only trigger recording if we're in the right state and no request or reset is in progress
      if (combinedSignalStrength > ambientBaseline * CONFIG.audio.listeningTriggerMultiplier && 
          !isProcessingRequestRef.current && 
          !resetInProgressRef.current) {
        startRecording();
      }
    }
  };

  // ========================= WAVEFORM ANIMATION =========================
  useEffect(() => {
    let animationId;
    const animate = () => {
      updateWaveform();
      animationId = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(animationId);
  }, [status, ambientBaseline, silenceThreshold]);

  // ========================= IMAGE CAPTURE =========================
  /**
   * Captures an image from the camera
   */
  const captureImageFromCamera = async () => {
    if (!videoTrackRef.current) {
      console.error('Camera is not available.');
      return null;
    }
    try {
      const imageCapture = new ImageCapture(videoTrackRef.current);
      const blob = await imageCapture.takePhoto();
      return blob;
    } catch (err) {
      console.error('Error capturing image from camera:', err);
      return null;
    }
  };

  // ========================= RECORDING FUNCTIONS =========================
  /**
   * Starts audio recording
   */
  const startRecording = () => {
    if (status !== 'listening' || isProcessingRequestRef.current || resetInProgressRef.current) return;
    
    setStatus('recording');
    recordingValidRef.current = false; // Reset validation flag
    recordingStartTimeRef.current = Date.now(); // Track when recording started
    lastSoundTimeRef.current = Date.now(); // Reset last sound time
    setSilenceDuration(0);
    setIsSilent(false);
    previousSilenceStateRef.current = false; // Reset hysteresis state
    
    try {
      const mediaRecorder = new MediaRecorder(audioStreamRef.current);
      audioChunksRef.current = [];
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const recordingDuration = Date.now() - recordingStartTimeRef.current;
        
        // Validate recording - must be valid audio that exceeds minimum duration
        // The bug was here - the condition had a logical error with the < operator
        if (recordingValidRef.current && recordingDuration >= CONFIG.timing.minValidRecordingDuration) {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
          setAudioFile(audioBlob);
          setStatus('processing');
          // Set the processing flag BEFORE starting the request
          isProcessingRequestRef.current = true;
          processRecording();
        }
        else {
          // If recording is invalid, reset the state
          console.log('Recording was not valid or too short. Resetting...');
          resetRecording();
        }
      };
      
      mediaRecorder.start();
    } catch (err) {
      console.error('Error starting recording:', err);
      setStatus('error');
    }
  };

  /**
   * Stops the current recording
   */
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      // Validation is done in the onstop callback of MediaRecorder
    } else {
      console.error('Recording is not active or has already been stopped.');
      setStatus('error');
    }
  };

  /**
   * Resets the recording state
   */
  const resetRecording = () => {
    // Set flag to prevent multiple resets
    if (resetInProgressRef.current) return;
    resetInProgressRef.current = true;
    
    // Ensure the processing flag is cleared
    isProcessingRequestRef.current = false;
    
    setAudioFile(null);
    setAudioUrl(null);
    setSoundWave(Array(50).fill(0));
    setSilenceDuration(0);
    setIsSilent(false);
    previousSilenceStateRef.current = false;
    
    // Wait a short time before allowing new recordings
    setTimeout(() => {
      setStatus('listening');
      resetInProgressRef.current = false;
    }, 300);
  };

  // ========================= API FUNCTIONS =========================
  /**
   * Process the recording by uploading audio and image data to the server
   */
  const processRecording = async () => {
    if (!audioFile) {
      isProcessingRequestRef.current = false;
      setStatus('error');
      return;
    }

    const formData = new FormData();
    formData.append('audio', audioFile, 'recording.wav');

    try {
      const imageBlob = await captureImageFromCamera();
      if (imageBlob) {
        formData.append('image', imageBlob, 'snapshot.png');
      }

      const endpoint = `${CONFIG.api.baseUrl}${CONFIG.api.audioImageEndpoint}`;
      
      await axios.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const audioResponse = await axios.get(`${CONFIG.api.baseUrl}${CONFIG.api.audioOutputPath}`, {
        responseType: 'blob'
      });
      
      const processedAudioUrl = URL.createObjectURL(audioResponse.data);
      setAudioUrl(processedAudioUrl);
      setStatus('completed');
      
      // Play audio programmatically
      if (audioRef.current) {
        audioRef.current.src = processedAudioUrl;
        audioRef.current.play();
      }
    } catch (err) {
      console.error('Error sending data:', err);
      setStatus('error');
    } finally {
      // Always reset the processing flag when complete
      isProcessingRequestRef.current = false;
    }
  };

  // ========================= RENDER =========================
  return (
    <div className="relative min-h-screen bg-black flex items-center justify-center p-6">
      <div className="grid grid-cols-2 gap-6 w-full max-w-6xl">
        {/* Left side - LED Face */}
        <div className="flex flex-col h-full">
          <div className="bg-gray-800 rounded-lg overflow-hidden flex-grow">
            <LEDFace emotion={STATUS_INFO[status].emotion} />
          </div>
          <div className="mt-4 text-center text-white text-xl">
            {status === 'recording' && isSilent 
              ? `Gravando (Silêncio detectado)...` 
              : STATUS_INFO[status].message}
          </div>
          {status === 'recording' && isSilent && (
            <div className="text-center text-amber-300 mt-2">
              Silêncio: {Math.round(silenceDuration / 100) / 10}s
            </div>
          )}
          
          {/* Calibration debug info */}
          {(status === 'listening' || status === 'recording') && (
            <div className="mt-2 text-xs text-gray-400">
              Baseline: {debugCalibration.baseline.toFixed(1)} | 
              Threshold: {debugCalibration.threshold.toFixed(1)} | 
              Current: {debugCalibration.currentLevel.toFixed(1)}
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
          
          {/* Audio waveform with silence threshold indicator */}
          <div className="mt-4 bg-gray-800 rounded-lg p-4 h-32 relative">
            {/* Silence threshold line */}
            <div 
              className="absolute left-0 right-0 border-t border-red-500/50 pointer-events-none"
              style={{
                top: `${100 - Math.min((silenceThreshold / 100) * 100, 100)}%`,
              }}
            >
              <span className="absolute right-1 top-0 transform -translate-y-full text-red-500/80 text-xs">
                Threshold
              </span>
            </div>
            
            <div className="flex items-center justify-center h-full gap-1">
              {soundWave.map((height, index) => (
                <div
                  key={index}
                  className={`w-1 ${height < silenceThreshold ? 'bg-gray-500' : 'bg-amber-500'}`}
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