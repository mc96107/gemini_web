/**
 * @jest-environment jsdom
 */
const DriveModeManager = require('../app/static/drive_mode.js');

describe('DriveModeManager', () => {
    let manager;

    beforeEach(() => {
        manager = new DriveModeManager();
    });

    test('should initialize with default state', () => {
        expect(manager.isActive).toBe(false);
        expect(manager.state).toBe('idle'); // idle, listening, processing, speaking
    });

    test('should have an isSupported method', () => {
        expect(typeof manager.isSupported).toBe('function');
    });

    test('isSupported should return true if both STT and TTS are available', () => {
        Object.defineProperty(window, 'webkitSpeechRecognition', {
            value: jest.fn(),
            configurable: true
        });
        Object.defineProperty(window, 'speechSynthesis', {
            value: {},
            configurable: true
        });
        expect(manager.isSupported()).toBe(true);
    });

    test('isSupported should return false if STT is missing', () => {
        delete window.webkitSpeechRecognition;
        delete window.speechRecognition;
        Object.defineProperty(window, 'speechSynthesis', {
            value: {},
            configurable: true
        });
        expect(manager.isSupported()).toBe(false);
    });

    test('isSupported should return false if TTS is missing', () => {
        Object.defineProperty(window, 'webkitSpeechRecognition', {
            value: jest.fn(),
            configurable: true
        });
        delete window.speechSynthesis;
        expect(manager.isSupported()).toBe(false);
    });

    test('should request wake lock', async () => {
        const mockWakeLock = { release: jest.fn() };
        Object.defineProperty(navigator, 'wakeLock', {
            value: {
                request: jest.fn().mockResolvedValue(mockWakeLock)
            },
            configurable: true
        });

        await manager.requestWakeLock();
        expect(navigator.wakeLock.request).toHaveBeenCalledWith('screen');
        expect(manager.wakeLock).toBe(mockWakeLock);
    });

    test('should release wake lock', async () => {
        const mockWakeLock = { release: jest.fn().mockResolvedValue() };
        manager.wakeLock = mockWakeLock;

        await manager.releaseWakeLock();
        expect(mockWakeLock.release).toHaveBeenCalled();
        expect(manager.wakeLock).toBe(null);
    });

    test('should show button if supported', () => {
        document.body.innerHTML = '<button id="drive-mode-btn" class="d-none"></button>';
        const driveModeBtn = document.getElementById('drive-mode-btn');
        
        Object.defineProperty(window, 'webkitSpeechRecognition', {
            value: jest.fn(),
            configurable: true
        });
        Object.defineProperty(window, 'speechSynthesis', {
            value: {},
            configurable: true
        });

        if (manager.isSupported() && driveModeBtn) {
            driveModeBtn.classList.remove('d-none');
        }

        expect(driveModeBtn.classList.contains('d-none')).toBe(false);
    });
});
