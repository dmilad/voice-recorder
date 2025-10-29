"""Configuration management for voice recorder."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    # Whisper settings
    whisper_model: str = os.getenv("WHISPER_MODEL", "base.en")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")

    # Audio settings
    sample_rate: int = int(os.getenv("SAMPLE_RATE", "16000"))
    channels: int = int(os.getenv("CHANNELS", "1"))

    # Recording settings
    max_recording_duration: int = int(os.getenv("MAX_RECORDING_DURATION", "300"))  # 5 minutes
    min_recording_duration: float = float(os.getenv("MIN_RECORDING_DURATION", "0.5"))

    # Silence detection
    enable_silence_detection: bool = os.getenv("ENABLE_SILENCE_DETECTION", "true").lower() == "true"
    energy_threshold: float = float(os.getenv("ENERGY_THRESHOLD", "0.01"))

    # Clipboard settings
    restore_clipboard: bool = os.getenv("RESTORE_CLIPBOARD", "true").lower() == "true"
    paste_delay_ms: int = int(os.getenv("PASTE_DELAY_MS", "100"))

    # Hotkey
    hotkey: str = os.getenv("HOTKEY", "<cmd>+<alt>+<space>")

    def __post_init__(self):
        """Validate configuration."""
        if self.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            raise ValueError(f"Invalid sample rate: {self.sample_rate}")

        if self.channels not in [1, 2]:
            raise ValueError(f"Invalid number of channels: {self.channels}")

        if self.max_recording_duration <= 0:
            raise ValueError("Max recording duration must be positive")

        if self.min_recording_duration <= 0:
            raise ValueError("Min recording duration must be positive")


# Global config instance
config = Config()
