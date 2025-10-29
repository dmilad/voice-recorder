"""Global hotkey listener."""

from typing import Callable
from pynput import keyboard
from .config import config


class HotkeyListener:
    """Listens for global hotkey presses."""

    def __init__(self, on_hotkey: Callable[[], None]):
        """
        Initialize hotkey listener.

        Args:
            on_hotkey: Callback function to call when hotkey is pressed
        """
        self.on_hotkey = on_hotkey
        self.listener = None

    def start(self) -> None:
        """Start listening for hotkeys."""
        print(f"Setting up hotkey: {config.hotkey}")
        print(f"Press {config.hotkey} to start/stop recording")

        try:
            # Create listener with global hotkeys
            self.listener = keyboard.GlobalHotKeys({config.hotkey: self.on_hotkey})
            self.listener.start()
            print("Hotkey listener started successfully")
        except Exception as e:
            print(f"Error starting hotkey listener: {e}")
            print("\nNote: This requires Accessibility permissions.")
            print("Go to: System Settings → Privacy & Security → Accessibility")
            print("Add Terminal or your Python executable to the list.")
            raise

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        if self.listener:
            self.listener.stop()
            self.listener = None
            print("Hotkey listener stopped")

    def wait(self) -> None:
        """Wait for the listener to finish (blocking)."""
        if self.listener:
            self.listener.join()

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop()
