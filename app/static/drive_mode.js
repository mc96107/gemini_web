/**
 * Manages the "Drive Mode" voice-only conversation loop.
 * Handles speech recognition (STT) and speech synthesis (TTS).
 */
class DriveModeManager {
    constructor() {
        this.isActive = false;
        this.state = 'idle'; // idle, listening, processing, speaking
        this.wakeLock = null;
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
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DriveModeManager;
}
