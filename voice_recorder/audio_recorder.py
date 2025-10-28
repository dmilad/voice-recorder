"""Audio recording functionality."""

import numpy as np
import sounddevice as sd
from typing import Optional, Callable
from .config import config


class AudioRecorder:
    """Records audio from the microphone."""

    def __init__(self, on_audio_chunk: Optional[Callable[[np.ndarray], None]] = None):
        """
        Initialize audio recorder.

        Args:
            on_audio_chunk: Callback function called for each audio chunk
        """
        self.on_audio_chunk = on_audio_chunk
        self.stream: Optional[sd.InputStream] = None
        self._is_recording = False

    def start_recording(self) -> None:
        """Start recording audio."""
        if self._is_recording:
            print("Already recording")
            return

        print(f"Starting audio recording at {config.sample_rate}Hz...")

        def audio_callback(indata: np.ndarray, frames: int, time_info, status):
            """Callback function for audio stream."""
            if status:
                print(f"Audio status: {status}")

            # Copy the audio data and send to callback
            if self.on_audio_chunk:
                # Convert to 1D array and copy
                audio_chunk = indata[:, 0].copy() if config.channels == 1 else indata.copy()
                self.on_audio_chunk(audio_chunk)

        try:
            self.stream = sd.InputStream(
                samplerate=config.sample_rate,
                channels=config.channels,
                dtype=np.float32,
                callback=audio_callback,
            )
            self.stream.start()
            self._is_recording = True
            print("Recording started")
        except Exception as e:
            print(f"Error starting recording: {e}")
            raise

    def stop_recording(self) -> None:
        """Stop recording audio."""
        if not self._is_recording:
            print("Not currently recording")
            return

        print("Stopping audio recording...")

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        self._is_recording = False
        print("Recording stopped")

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    def __del__(self):
        """Cleanup when object is destroyed."""
        if self._is_recording:
            self.stop_recording()


def check_audio_devices() -> None:
    """Print available audio devices."""
    print("\nAvailable audio devices:")
    print(sd.query_devices())
    print(f"\nDefault input device: {sd.query_devices(kind='input')['name']}")


def calculate_energy(audio_data: np.ndarray) -> float:
    """
    Calculate RMS energy of audio data.

    Args:
        audio_data: Audio samples as numpy array

    Returns:
        RMS energy value
    """
    return float(np.sqrt(np.mean(audio_data**2)))


def is_silent(audio_data: np.ndarray, threshold: Optional[float] = None) -> bool:
    """
    Check if audio is silent based on energy threshold.

    Args:
        audio_data: Audio samples as numpy array
        threshold: Energy threshold (uses config default if not provided)

    Returns:
        True if audio is silent, False otherwise
    """
    if threshold is None:
        threshold = config.energy_threshold

    energy = calculate_energy(audio_data)
    return energy < threshold
