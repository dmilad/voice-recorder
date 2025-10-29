"""State management for recording sessions."""

import threading
from enum import Enum, auto
from typing import Optional
import numpy as np


class RecordingState(Enum):
    """Recording states."""

    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()


class StateManager:
    """Thread-safe state management for recording sessions."""

    def __init__(self):
        """Initialize state manager."""
        self._state = RecordingState.IDLE
        self._lock = threading.Lock()
        self._audio_buffer: list[np.ndarray] = []
        self._last_transcription: str = ""

    @property
    def state(self) -> RecordingState:
        """Get current state."""
        with self._lock:
            return self._state

    def transition_to(self, new_state: RecordingState) -> bool:
        """
        Attempt to transition to a new state.

        Args:
            new_state: The state to transition to

        Returns:
            True if transition was successful, False otherwise
        """
        with self._lock:
            # Define valid transitions
            valid_transitions = {
                RecordingState.IDLE: [RecordingState.RECORDING],
                RecordingState.RECORDING: [RecordingState.PROCESSING, RecordingState.IDLE],
                RecordingState.PROCESSING: [RecordingState.IDLE],
            }

            if new_state in valid_transitions.get(self._state, []):
                print(f"State transition: {self._state.name} -> {new_state.name}")
                self._state = new_state
                return True
            else:
                print(f"Invalid state transition: {self._state.name} -> {new_state.name}")
                return False

    def add_audio_chunk(self, chunk: np.ndarray) -> None:
        """
        Add an audio chunk to the buffer.

        Args:
            chunk: Audio data as numpy array
        """
        with self._lock:
            self._audio_buffer.append(chunk)

    def get_audio_data(self) -> Optional[np.ndarray]:
        """
        Get all audio data and clear the buffer.

        Returns:
            Concatenated audio data or None if buffer is empty
        """
        with self._lock:
            if not self._audio_buffer:
                return None

            audio_data = np.concatenate(self._audio_buffer)
            self._audio_buffer.clear()
            return audio_data

    def clear_buffer(self) -> None:
        """Clear the audio buffer."""
        with self._lock:
            self._audio_buffer.clear()

    def is_idle(self) -> bool:
        """Check if state is IDLE."""
        return self.state == RecordingState.IDLE

    def is_recording(self) -> bool:
        """Check if state is RECORDING."""
        return self.state == RecordingState.RECORDING

    def is_processing(self) -> bool:
        """Check if state is PROCESSING."""
        return self.state == RecordingState.PROCESSING

    def set_last_transcription(self, text: str) -> None:
        """
        Store the last transcription.

        Args:
            text: The transcribed text
        """
        with self._lock:
            self._last_transcription = text

    def get_last_transcription(self) -> str:
        """
        Get the last transcription.

        Returns:
            The last transcribed text
        """
        with self._lock:
            return self._last_transcription
