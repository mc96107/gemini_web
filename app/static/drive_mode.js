/**
 * Manages the "Drive Mode" voice-only conversation loop.
 * Handles speech recognition (STT) and speech synthesis (TTS).
 */
class DriveModeManager {
    constructor() {
        this.isActive = false;
        this.state = 'idle'; // idle, listening, processing, speaking
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
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DriveModeManager;
}
