import os
import datetime
import ctypes
import pyautogui
import pyperclip
from pycaw.pycaw import AudioUtilities

def lock_pc():
    print("[System] Locking PC...")
    ctypes.windll.user32.LockWorkStation()

def mute_volume():
    print("[System] Toggling volume mute...")
    device = AudioUtilities.GetSpeakers()
    volume = device.EndpointVolume
    current_mute = volume.GetMute()
    volume.SetMute(not current_mute, None)

def set_volume_percent(percent):
    device = AudioUtilities.GetSpeakers()
    # Ensure value is bounded between 0 and 100
    level = max(0.0, min(100.0, float(percent)))
    device.volume_percent = level
    print(f"[System] Volume set to {int(level)}%")

def change_volume_by(delta):
    device = AudioUtilities.GetSpeakers()
    current = device.volume_percent
    new_level = max(0.0, min(100.0, current + delta))
    device.volume_percent = new_level
    print(f"[System] Volume adjusted to {int(new_level)}%")

def take_screenshot():
    folder = "screenshots"
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(folder, f"screenshot_{timestamp}.png")
    screenshot = pyautogui.screenshot()
    screenshot.save(filepath)
    print(f"[System] Screenshot saved at: {filepath}")
    return filepath

def write_note(note_text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("notes.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {note_text}\n")
    print(f"[System] Note recorded: {note_text}")

def get_clipboard():
    text = pyperclip.paste()
    return text.strip() if text else ""