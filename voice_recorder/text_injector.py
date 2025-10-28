"""Text injection via clipboard and keyboard simulation."""

import time
import pyperclip
from pynput.keyboard import Controller, Key
from .config import config


class TextInjector:
    """Injects text into the active application via clipboard."""

    def __init__(self):
        """Initialize text injector."""
        self.keyboard = Controller()

    def paste_text(self, text: str) -> bool:
        """
        Paste text into the active application.

        Args:
            text: Text to paste

        Returns:
            True if successful, False otherwise
        """
        if not text:
            print("No text to paste")
            return False

        try:
            # Save current clipboard content if configured
            original_clipboard = None
            if config.restore_clipboard:
                try:
                    original_clipboard = pyperclip.paste()
                except Exception as e:
                    print(f"Warning: Could not save clipboard: {e}")

            # Copy text to clipboard
            pyperclip.copy(text)
            print(f"Copied {len(text)} characters to clipboard")

            # Wait a bit for clipboard to update
            time.sleep(config.paste_delay_ms / 1000.0)

            # Simulate Cmd+V to paste
            with self.keyboard.pressed(Key.cmd):
                self.keyboard.press("v")
                self.keyboard.release("v")

            print("Pasted text to active application")

            # Restore original clipboard if configured
            if config.restore_clipboard and original_clipboard is not None:
                # Wait a bit before restoring
                time.sleep(0.2)
                try:
                    pyperclip.copy(original_clipboard)
                    print("Restored original clipboard")
                except Exception as e:
                    print(f"Warning: Could not restore clipboard: {e}")

            return True

        except Exception as e:
            print(f"Error pasting text: {e}")
            return False

    def copy_to_clipboard_only(self, text: str) -> bool:
        """
        Copy text to clipboard without pasting.

        Args:
            text: Text to copy

        Returns:
            True if successful, False otherwise
        """
        if not text:
            return False

        try:
            pyperclip.copy(text)
            print(f"Copied {len(text)} characters to clipboard")
            return True
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            return False
