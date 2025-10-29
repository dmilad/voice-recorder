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
        self._processed_sample_index: int = 0  # Track how many samples have been transcribed

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
            self._processed_sample_index = 0

    def get_next_chunk(self, chunk_size_samples: int, overlap_samples: int = 0) -> Optional[np.ndarray]:
        """
        Get the next chunk of audio for transcription without clearing the buffer.
        Allows recording to continue while chunks are being transcribed.

        Args:
            chunk_size_samples: Number of samples to retrieve
            overlap_samples: Number of samples to overlap with previous chunk for context

        Returns:
            Audio chunk as numpy array or None if not enough new audio available
        """
        with self._lock:
            if not self._audio_buffer:
                return None

            # Get total samples in buffer
            total_samples = sum(len(chunk) for chunk in self._audio_buffer)

            # Calculate start position (accounting for overlap)
            start_idx = max(0, self._processed_sample_index - overlap_samples)
            end_idx = start_idx + chunk_size_samples + overlap_samples

            # Check if we have enough new audio
            if self._processed_sample_index >= total_samples:
                return None  # No new audio available

            # If we don't have a full chunk yet, only return None if we're still recording
            # (this will be checked by the caller based on recording state)
            available_new_samples = total_samples - self._processed_sample_index
            if available_new_samples < chunk_size_samples:
                # Not enough for a full chunk yet
                return None

            # Concatenate buffer and extract chunk
            full_audio = np.concatenate(self._audio_buffer)
            chunk = full_audio[start_idx:min(end_idx, total_samples)]

            return chunk

    def mark_chunk_processed(self, num_samples: int) -> None:
        """
        Mark a number of samples as processed (transcribed).

        Args:
            num_samples: Number of samples that have been processed
        """
        with self._lock:
            self._processed_sample_index += num_samples

    def get_remaining_audio(self, overlap_samples: int = 0) -> Optional[np.ndarray]:
        """
        Get all remaining unprocessed audio (for final pass after recording stops).

        Args:
            overlap_samples: Number of samples to include before the unprocessed section

        Returns:
            Remaining audio as numpy array or None if no unprocessed audio
        """
        with self._lock:
            if not self._audio_buffer:
                return None

            total_samples = sum(len(chunk) for chunk in self._audio_buffer)

            # If everything is processed, return None
            if self._processed_sample_index >= total_samples:
                return None

            # Get from (processed_index - overlap) to end
            start_idx = max(0, self._processed_sample_index - overlap_samples)
            full_audio = np.concatenate(self._audio_buffer)

            return full_audio[start_idx:]

    def get_total_samples(self) -> int:
        """
        Get total number of samples currently in buffer.

        Returns:
            Total sample count
        """
        with self._lock:
            if not self._audio_buffer:
                return 0
            return sum(len(chunk) for chunk in self._audio_buffer)

    def get_processed_samples(self) -> int:
        """
        Get number of samples that have been processed.

        Returns:
            Processed sample count
        """
        with self._lock:
            return self._processed_sample_index

    def reset_chunk_tracking(self) -> None:
        """Reset chunk processing tracking (call when starting new recording)."""
        with self._lock:
            self._processed_sample_index = 0

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

    def clear_transcription(self) -> None:
        """Clear the last transcription."""
        with self._lock:
            self._last_transcription = ""
