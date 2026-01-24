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
        global.window = {
            webkitSpeechRecognition: jest.fn(),
            speechSynthesis: {}
        };
        expect(manager.isSupported()).toBe(true);
    });

    test('isSupported should return false if STT is missing', () => {
        global.window = {
            speechSynthesis: {}
        };
        expect(manager.isSupported()).toBe(false);
    });

    test('isSupported should return false if TTS is missing', () => {
        global.window = {
            webkitSpeechRecognition: jest.fn()
        };
        expect(manager.isSupported()).toBe(false);
    });
});
