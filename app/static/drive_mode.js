/**
 * Manages the "Drive Mode" voice-only conversation loop.
 * Handles speech recognition (STT) and speech synthesis (TTS).
 */
class DriveModeManager {
    constructor() {
        this.isActive = false;
        this.state = 'idle'; // idle, listening, processing, speaking
        this.wakeLock = null;
        
        // Pre-load voices for Chrome/Android
        if (typeof window !== 'undefined' && window.speechSynthesis) {
            window.speechSynthesis.getVoices();
            window.speechSynthesis.onvoiceschanged = () => {
                window.speechSynthesis.getVoices();
            };
        }
    }

    /**
     * Checks if the browser supports the necessary Web Speech APIs and Wake Lock API.
     * @returns {boolean}
     */
    isSupported() {
        const hasSTT = 'webkitSpeechRecognition' in window || 'speechRecognition' in window;
        const hasTTS = 'speechSynthesis' in window;
        return hasSTT && hasTTS;
    }

    /**
     * Requests a screen wake lock to prevent the device from sleeping.
     */
    async requestWakeLock() {
        if ('wakeLock' in navigator) {
            try {
                this.wakeLock = await navigator.wakeLock.request('screen');
                console.log('Wake Lock acquired');
            } catch (err) {
                console.error(`${err.name}, ${err.message}`);
            }
        }
    }

    /**
     * Releases the acquired wake lock.
     */
    async releaseWakeLock() {
        if (this.wakeLock) {
            await this.wakeLock.release();
            this.wakeLock = null;
            console.log('Wake Lock released');
        }
    }

    /**
     * Starts the Speech-to-Text (STT) recognition.
     * @param {Function} onResult - Callback called with transcribed text.
     * @param {Function} onError - Callback called on recognition error.
     */
    startListening(onResult, onError) {
        const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
        if (!SpeechRecognition) {
            if (onError) onError('Speech Recognition not supported');
            return;
        }

        const recognition = new SpeechRecognition();
        
        // Using el-GR generally allows for better recognition of Greek + English
        // mixed together than using en-US on an English device.
        recognition.lang = 'el-GR'; 
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        recognition.continuous = false; // We want automatic end-of-speech detection

        recognition.onstart = () => {
            this.state = 'listening';
            console.log('STT: Started listening...');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            console.log('STT Result:', transcript);
            this.state = 'idle';
            if (onResult) onResult(transcript);
        };

        recognition.onerror = (event) => {
            console.error('STT Error:', event.error);
            this.state = 'idle';
            if (onError) onError(event.error);
        };

        recognition.onend = () => {
            console.log('STT: Stopped listening.');
            if (this.state === 'listening') {
                this.state = 'idle';
            }
        };

        try {
            recognition.start();
            this.recognition = recognition;
        } catch (e) {
            console.error('STT Start Error:', e);
            this.state = 'idle';
            if (onError) onError(e.message);
        }
    }

    /**
     * Stops current recognition.
     */
    stopListening() {
        if (this.recognition) {
            try {
                this.recognition.stop();
            } catch (e) {
                // Ignore if already stopped
            }
            this.recognition = null;
        }
    }

    /**
     * Reads text aloud using Speech Synthesis (TTS).
     * @param {string} text - The text to speak.
     * @param {Function} onEnd - Callback called when speaking finishes.
     */
    speak(text, onEnd) {
        if (!window.speechSynthesis) {
            if (onEnd) onEnd();
            return;
        }

        // Cancel any ongoing speech
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        
        // Smarter Voice Selection
        const voices = window.speechSynthesis.getVoices();
        if (voices.length > 0) {
            // Detect if text is mostly Greek or English (simplified)
            const isGreek = /[\u0370-\u03FF]/.test(text);
            const targetLang = isGreek ? 'el' : 'en';
            
            // Find a voice that matches the language
            const voice = voices.find(v => v.lang.startsWith(targetLang)) || 
                          voices.find(v => v.lang.startsWith(document.documentElement.lang)) ||
                          voices[0];
            
            if (voice) {
                utterance.voice = voice;
                utterance.lang = voice.lang;
            }
        } else {
            utterance.lang = document.documentElement.lang || window.navigator.language || 'el-GR';
        }
        
        utterance.onstart = () => {
            this.state = 'speaking';
            console.log('TTS: Started speaking...');
        };

        utterance.onend = () => {
            this.state = 'idle';
            console.log('TTS: Finished speaking.');
            if (onEnd) onEnd();
        };

        utterance.onerror = (event) => {
            console.error('TTS Error:', event.error);
            this.state = 'idle';
            if (onEnd) onEnd();
        };

        window.speechSynthesis.speak(utterance);
    }

    /**
     * Stops current speaking.
     */
    stopSpeaking() {
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DriveModeManager;
}
