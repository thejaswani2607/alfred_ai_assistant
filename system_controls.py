import ctypes

def lock_pc():
    print("[System] Locking PC...")
    # Native Windows command to lock the workstation
    ctypes.windll.user32.LockWorkStation()

def mute_volume():
    print("[System] Toggling volume mute...")
    # Native Windows virtual key code for Volume Mute
    VK_VOLUME_MUTE = 0xAD
    ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)