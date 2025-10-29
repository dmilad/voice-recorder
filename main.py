#!/usr/bin/env python3
"""
Voice Recorder - Local voice-to-text with global hotkey.

Press Cmd+Shift+Space to start/stop recording.
"""

import sys
import signal
import threading
import time
from typing import Literal, Optional
from voice_recorder.config import config
from voice_recorder.state_manager import StateManager, RecordingState
from voice_recorder.audio_recorder import AudioRecorder, is_silent
from voice_recorder.transcriber import Transcriber
from voice_recorder.text_injector import TextInjector
from voice_recorder.hotkey_listener import HotkeyListener
from voice_recorder.ui import VoiceRecorderUI


class VoiceRecorderApp:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.state_manager = StateManager()
        self.transcriber = Transcriber()
        self.text_injector = TextInjector()
        self.audio_recorder = AudioRecorder(on_audio_chunk=self._on_audio_chunk)
        self.hotkey_listener = HotkeyListener(on_hotkey=self._on_hotkey_pressed)
        self.ui: VoiceRecorderUI | None = None
        self.running = True
        self.recording_source: Literal["hotkey", "ui_button"] = "hotkey"

        # Chunked transcription state
        self._chunked_transcription_thread: Optional[threading.Thread] = None
        self._stop_chunked_transcription = threading.Event()
        self._accumulated_transcription = ""
        self._recording_start_time: float = 0.0

    def _on_audio_chunk(self, chunk):
        """Called when a new audio chunk is available."""
        if self.state_manager.is_recording():
            self.state_manager.add_audio_chunk(chunk)

    def _on_hotkey_pressed(self):
        """Called when the hotkey is pressed."""
        print("\n--- Hotkey pressed ---")
        self.recording_source = "hotkey"
        self._toggle_recording()

    def _on_ui_record_pressed(self):
        """Called when the UI record button is pressed."""
        print("\n--- UI Record button pressed ---")
        self.recording_source = "ui_button"
        self._toggle_recording()

    def _on_ui_clear_pressed(self):
        """Called when the UI clear button is pressed."""
        print("\n--- UI Clear button pressed ---")
        self.state_manager.clear_transcription()
        self._update_ui_transcription("")

        # Clean up any temporary files from chunked transcription
        self.transcriber.cleanup_temp_files()

        # Clear accumulated transcription
        self._accumulated_transcription = ""

        print("✅ Text and temp files cleared")

    def _toggle_recording(self):
        """Toggle recording state."""
        if self.state_manager.is_idle():
            # Start recording
            if self.state_manager.transition_to(RecordingState.RECORDING):
                self.state_manager.reset_chunk_tracking()
                self._accumulated_transcription = ""
                self._recording_start_time = time.time()
                self.audio_recorder.start_recording()
                print("🎤 Recording... (Press hotkey/button again to stop)")
                self._update_ui_state("RECORDING")

                # Start chunked transcription for UI mode
                if config.enable_chunked_transcription and self.recording_source == "ui_button":
                    self._stop_chunked_transcription.clear()
                    self._chunked_transcription_thread = threading.Thread(
                        target=self._chunked_transcription_worker,
                        daemon=True
                    )
                    self._chunked_transcription_thread.start()
                    print("📊 Chunked transcription enabled")

        elif self.state_manager.is_recording():
            # Stop recording and process
            self.audio_recorder.stop_recording()

            # Signal chunked transcription to stop
            if self._chunked_transcription_thread and self._chunked_transcription_thread.is_alive():
                self._stop_chunked_transcription.set()

            if self.state_manager.transition_to(RecordingState.PROCESSING):
                self._update_ui_state("PROCESSING")
                # Process in a separate thread to avoid blocking
                threading.Thread(target=self._process_recording, daemon=True).start()

        elif self.state_manager.is_processing():
            print("⏳ Still processing previous recording, please wait...")

    def _chunked_transcription_worker(self):
        """Worker thread for chunked transcription during recording."""
        print("🔄 Chunked transcription worker started")

        chunk_size_samples = config.chunk_duration_seconds * config.sample_rate
        overlap_samples = config.chunk_overlap_seconds * config.sample_rate
        chunk_count = 0

        try:
            while not self._stop_chunked_transcription.is_set():
                # Check if we have enough audio for a chunk
                chunk_audio = self.state_manager.get_next_chunk(
                    chunk_size_samples=chunk_size_samples,
                    overlap_samples=overlap_samples
                )

                if chunk_audio is not None:
                    chunk_count += 1
                    print(f"\n📦 Processing chunk #{chunk_count}...")

                    # Calculate progress
                    processed_seconds = self.state_manager.get_processed_samples() / config.sample_rate
                    total_seconds = self.state_manager.get_total_samples() / config.sample_rate

                    # Update UI with progress
                    self._update_ui_progress(processed_seconds, total_seconds)
                    self._update_ui_status(f"Transcribing chunk {chunk_count}...", "blue")

                    try:
                        # Transcribe chunk with context from previous chunks
                        chunk_text = self.transcriber.transcribe_chunk_with_context(
                            audio_data=chunk_audio,
                            previous_text=self._accumulated_transcription,
                            progress_callback=lambda msg: print(f"  {msg}")
                        )

                        if chunk_text:
                            # Append to accumulated transcription
                            if self._accumulated_transcription:
                                self._accumulated_transcription += " " + chunk_text
                            else:
                                self._accumulated_transcription = chunk_text

                            # Update UI with accumulated text
                            self._update_ui_transcription(self._accumulated_transcription)
                            print(f"  ✅ Chunk #{chunk_count} complete: +{len(chunk_text)} chars")

                        # Mark chunk as processed (excluding overlap)
                        samples_processed = chunk_size_samples
                        self.state_manager.mark_chunk_processed(samples_processed)

                    except Exception as e:
                        print(f"  ❌ Error transcribing chunk #{chunk_count}: {e}")
                        self._update_ui_status(f"Error in chunk {chunk_count}", "orange")
                        # Continue with next chunk despite error

                else:
                    # No chunk available yet, wait a bit
                    time.sleep(1.0)

            print("🛑 Chunked transcription worker stopping...")

        except Exception as e:
            print(f"❌ Fatal error in chunked transcription worker: {e}")
            import traceback
            traceback.print_exc()

    def _process_recording(self):
        """Process the recorded audio."""
        try:
            # Check if we used chunked transcription
            used_chunked_transcription = (
                config.enable_chunked_transcription and
                self.recording_source == "ui_button" and
                self._chunked_transcription_thread is not None
            )

            if used_chunked_transcription:
                # Wait for chunked transcription thread to finish
                print("⏳ Waiting for chunked transcription to complete...")
                if self._chunked_transcription_thread.is_alive():
                    self._chunked_transcription_thread.join(timeout=10)

                # Process any remaining audio (final pass)
                print("🔄 Processing remaining audio...")
                overlap_samples = config.chunk_overlap_seconds * config.sample_rate
                remaining_audio = self.state_manager.get_remaining_audio(overlap_samples=overlap_samples)

                if remaining_audio is not None and len(remaining_audio) > 0:
                    duration = len(remaining_audio) / config.sample_rate
                    print(f"📦 Final chunk: {duration:.2f}s")

                    try:
                        final_text = self.transcriber.transcribe_chunk_with_context(
                            audio_data=remaining_audio,
                            previous_text=self._accumulated_transcription,
                            progress_callback=lambda msg: print(f"  {msg}")
                        )

                        if final_text:
                            if self._accumulated_transcription:
                                self._accumulated_transcription += " " + final_text
                            else:
                                self._accumulated_transcription = final_text

                            self._update_ui_transcription(self._accumulated_transcription)
                            print(f"  ✅ Final chunk complete: +{len(final_text)} chars")

                    except Exception as e:
                        print(f"  ⚠️  Error processing final chunk: {e}")

                # Use accumulated transcription
                text = self._accumulated_transcription

                # Cleanup temp files
                self.transcriber.cleanup_temp_files()

            else:
                # Traditional single-pass transcription (for hotkey mode or if chunking disabled)
                audio_data = self.state_manager.get_audio_data()

                if audio_data is None or len(audio_data) == 0:
                    print("⚠️  No audio data recorded")
                    self.state_manager.transition_to(RecordingState.IDLE)
                    self._update_ui_state("IDLE")
                    self._update_ui_status("No audio data recorded", "orange")
                    return

                # Check duration
                duration = len(audio_data) / config.sample_rate
                print(f"📊 Recorded {duration:.2f} seconds of audio")

                if duration < config.min_recording_duration:
                    print(f"⚠️  Recording too short (< {config.min_recording_duration}s)")
                    self.state_manager.transition_to(RecordingState.IDLE)
                    self._update_ui_state("IDLE")
                    self._update_ui_status("Recording too short", "orange")
                    return

                # Check if silent
                if config.enable_silence_detection and is_silent(audio_data):
                    print("⚠️  No speech detected (audio is silent)")
                    self.state_manager.transition_to(RecordingState.IDLE)
                    self._update_ui_state("IDLE")
                    self._update_ui_status("No speech detected", "orange")
                    return

                # Transcribe
                print("🔄 Transcribing...")
                text = self.transcriber.transcribe(audio_data)

            # Common validation and output handling
            if not text:
                print("⚠️  No text transcribed")
                self.state_manager.transition_to(RecordingState.IDLE)
                self._update_ui_state("IDLE")
                self._update_ui_status("No text transcribed", "orange")
                return

            print(f"✅ Transcribed: \"{text[:100]}{'...' if len(text) > 100 else ''}\"")
            print(f"   Total: {len(text)} characters")

            # Store transcription
            self.state_manager.set_last_transcription(text)

            # Handle based on recording source
            if self.recording_source == "hotkey":
                # Auto-insert mode (existing behavior)
                print("📋 Pasting text...")
                if self.text_injector.paste_text(text):
                    print("✅ Text pasted successfully!")
                    self._update_ui_status("Text pasted!", "green")
                else:
                    print("⚠️  Failed to paste text (copied to clipboard instead)")
                    self.text_injector.copy_to_clipboard_only(text)
                    self._update_ui_status("Copied to clipboard", "orange")
            else:
                # UI display mode
                print("📱 Displaying in UI...")
                self._update_ui_transcription(text)
                self._update_ui_status("Transcription complete!", "green")
                print("✅ Text displayed in UI")

        except Exception as e:
            print(f"❌ Error processing recording: {e}")
            import traceback
            traceback.print_exc()
            self._update_ui_status(f"Error: {str(e)}", "red")

        finally:
            # Cleanup and return to idle state
            self.transcriber.cleanup_temp_files()
            self.state_manager.transition_to(RecordingState.IDLE)
            self._update_ui_state("IDLE")
            self._accumulated_transcription = ""
            print("Ready for next recording")

    def _update_ui_state(self, state: str):
        """Update UI state (thread-safe)."""
        if self.ui:
            self.ui.queue_state_update(state)

    def _update_ui_transcription(self, text: str):
        """Update UI transcription (thread-safe)."""
        if self.ui:
            self.ui.queue_transcription_update(text)

    def _update_ui_status(self, message: str, color: str = "gray"):
        """Update UI status message (thread-safe)."""
        if self.ui:
            self.ui.queue_status_update(message, color)

    def _update_ui_progress(self, processed_seconds: float, total_seconds: float):
        """Update UI progress (thread-safe)."""
        if self.ui:
            self.ui.queue_progress_update(processed_seconds, total_seconds)

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
        print(f"\n⌨️  Press {config.hotkey.replace('<', '').replace('>', '').replace('cmd', 'Cmd').replace('alt', 'Option').replace('shift', 'Shift').replace('+', '+')} to record and auto-insert")
        print("🖱️  Use UI button to record and display in window")
        print("⌨️  Close window to quit\n")

        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            # Start hotkey listener in background thread (non-blocking)
            self.hotkey_listener.start()
            print("✅ Hotkey listener started")

            # Create and show UI (blocking - runs in main thread)
            self.ui = VoiceRecorderUI(
                on_record_pressed=self._on_ui_record_pressed,
                on_clear_pressed=self._on_ui_clear_pressed
            )
            print("✅ UI initialized\n")

            # Start UI main loop (blocks until window closes)
            self.ui.show()

        except KeyboardInterrupt:
            print("\n\nShutting down...")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            self.shutdown()

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
        if self.ui:
            try:
                self.ui.destroy()
            except Exception:
                pass  # UI might already be destroyed
        print("Goodbye!")


def main():
    """Main entry point."""
    app = VoiceRecorderApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
