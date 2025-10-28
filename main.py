#!/usr/bin/env python3
"""
Voice Recorder - Local voice-to-text with global hotkey.

Press Cmd+Shift+Space to start/stop recording.
"""

import sys
import signal
import threading
from voice_recorder.config import config
from voice_recorder.state_manager import StateManager, RecordingState
from voice_recorder.audio_recorder import AudioRecorder, is_silent
from voice_recorder.transcriber import Transcriber
from voice_recorder.text_injector import TextInjector
from voice_recorder.hotkey_listener import HotkeyListener


class VoiceRecorderApp:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.state_manager = StateManager()
        self.transcriber = Transcriber()
        self.text_injector = TextInjector()
        self.audio_recorder = AudioRecorder(on_audio_chunk=self._on_audio_chunk)
        self.hotkey_listener = HotkeyListener(on_hotkey=self._on_hotkey_pressed)
        self.running = True

    def _on_audio_chunk(self, chunk):
        """Called when a new audio chunk is available."""
        if self.state_manager.is_recording():
            self.state_manager.add_audio_chunk(chunk)

    def _on_hotkey_pressed(self):
        """Called when the hotkey is pressed."""
        print("\n--- Hotkey pressed ---")

        if self.state_manager.is_idle():
            # Start recording
            if self.state_manager.transition_to(RecordingState.RECORDING):
                self.audio_recorder.start_recording()
                print("🎤 Recording... (Press hotkey again to stop)")

        elif self.state_manager.is_recording():
            # Stop recording and process
            self.audio_recorder.stop_recording()

            if self.state_manager.transition_to(RecordingState.PROCESSING):
                # Process in a separate thread to avoid blocking
                threading.Thread(target=self._process_recording, daemon=True).start()

        elif self.state_manager.is_processing():
            print("⏳ Still processing previous recording, please wait...")

    def _process_recording(self):
        """Process the recorded audio."""
        try:
            # Get audio data
            audio_data = self.state_manager.get_audio_data()

            if audio_data is None or len(audio_data) == 0:
                print("⚠️  No audio data recorded")
                self.state_manager.transition_to(RecordingState.IDLE)
                return

            # Check duration
            duration = len(audio_data) / config.sample_rate
            print(f"📊 Recorded {duration:.2f} seconds of audio")

            if duration < config.min_recording_duration:
                print(f"⚠️  Recording too short (< {config.min_recording_duration}s)")
                self.state_manager.transition_to(RecordingState.IDLE)
                return

            # Check if silent
            if config.enable_silence_detection and is_silent(audio_data):
                print("⚠️  No speech detected (audio is silent)")
                self.state_manager.transition_to(RecordingState.IDLE)
                return

            # Transcribe
            print("🔄 Transcribing...")
            text = self.transcriber.transcribe(audio_data)

            if not text:
                print("⚠️  No text transcribed")
                self.state_manager.transition_to(RecordingState.IDLE)
                return

            print(f"✅ Transcribed: \"{text}\"")

            # Paste text
            print("📋 Pasting text...")
            if self.text_injector.paste_text(text):
                print("✅ Text pasted successfully!")
            else:
                print("⚠️  Failed to paste text (copied to clipboard instead)")
                self.text_injector.copy_to_clipboard_only(text)

        except Exception as e:
            print(f"❌ Error processing recording: {e}")

        finally:
            # Return to idle state
            self.state_manager.transition_to(RecordingState.IDLE)
            print("Ready for next recording")

    def run(self):
        """Run the application."""
        print("=" * 60)
        print("Voice Recorder - Local Voice-to-Text")
        print("=" * 60)
        print(f"\n📝 Configuration:")
        print(f"  Model: {config.whisper_model}")
        print(f"  Hotkey: {config.hotkey}")
        print(f"  Sample rate: {config.sample_rate}Hz")
        print(f"  Max duration: {config.max_recording_duration}s")
        print("\n⌨️  Press Cmd+Shift+Space to start/stop recording")
        print("⌨️  Press Ctrl+C to quit\n")

        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            # Start hotkey listener
            self.hotkey_listener.start()

            # Wait for listener (blocking)
            self.hotkey_listener.wait()

        except KeyboardInterrupt:
            print("\n\nShutting down...")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return 1

        return 0

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n\nShutting down gracefully...")
        self.shutdown()
        sys.exit(0)

    def shutdown(self):
        """Clean up resources."""
        self.running = False
        if self.audio_recorder.is_recording:
            self.audio_recorder.stop_recording()
        self.hotkey_listener.stop()
        print("Goodbye!")


def main():
    """Main entry point."""
    app = VoiceRecorderApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
