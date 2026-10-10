import os
import datetime
import ctypes
import pyautogui
import pyperclip
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

def get_volume_controller():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))

def lock_pc():
    print("[System] Locking PC...")
    ctypes.windll.user32.LockWorkStation()

def mute_volume():
    print("[System] Toggling volume mute...")
    volume = get_volume_controller()
    current_mute = volume.GetMute()
    volume.SetMute(not current_mute, None)

def set_volume_percent(percent):
    volume = get_volume_controller()
    # Ensure value is bounded between 0.0 and 1.0
    level = max(0.0, min(1.0, float(percent) / 100.0))
    volume.SetMasterVolumeLevelScalar(level, None)
    print(f"[System] Volume set to {int(level * 100)}%")

def change_volume_by(delta):
    volume = get_volume_controller()
    current = volume.GetMasterVolumeLevelScalar()
    new_level = max(0.0, min(1.0, current + (delta / 100.0)))
    volume.SetMasterVolumeLevelScalar(new_level, None)
    print(f"[System] Volume adjusted to {int(new_level * 100)}%")

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