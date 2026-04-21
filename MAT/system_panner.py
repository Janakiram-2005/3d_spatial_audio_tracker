import time
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from pynput import keyboard
import sys

def get_volume_interface():
    # Helper to get the default speakers' volume interface
    devices = AudioUtilities.GetSpeakers()
    if not devices:
        # Fallback for systems where GetSpeakers works differently?
        # But 'devices' usually is the singleton wrapper.
        raise Exception("No default speaker found.")
    
    # In this pycaw version, .EndpointVolume is the interface pointer
    return devices.EndpointVolume

def main():
    print("--- System-Wide Spatial Audio Panner ---")
    print("Controls:")
    print("  [LEFT ARROW]  Turn Head Left")
    print("  [RIGHT ARROW] Turn Head Right")
    print("  [ESC]         Exit and Center Audio")
    print("----------------------------------------")
    print("Open YouTube or Spotify and try it!")

    # 1. Get Volume Interface
    try:
        volume = get_volume_interface()
    except Exception as e:
        print(f"Error accessing audio device: {e}")
        return

    # Check channel count
    channel_count = volume.GetChannelCount()
    if channel_count < 2:
        print(f"Error: Need stereo output. Found {channel_count} channels.")
        return
        
    print(f"Audio Device Connected. Channels: {channel_count}")

    # State
    yaw = 0.0 # Head angle in degrees. Positive = Right, Negative = Left.
    current_keys = set()
    running = True

    def update_audio():
        # Source is FIXED at 0 degrees (Front).
        # Relative angle of source to head:
        # If I turn Right (+90), Source is at -90 (Left).
        # If I turn Left (-90), Source is at +90 (Right).
        
        source_angle = -yaw 
        
        # Clamp Logic:
        # At 0 deg (Center): L=1, R=1.
        # At -90 deg (Source Left): L=1, R=0.
        # At +90 deg (Source Right): L=0, R=1.
        
        # Normalize angle to range [-90, 90] for calculations
        # (If user spins 360, we just modulo or clamp, for now clamp)
        eff_angle = max(-90, min(90, source_angle))
        
        # Calculate scalars
        # Right falls off as source moves left (angle < 0)
        # Left falls off as source moves right (angle > 0)
        
        left_vol = min(1.0, 1.0 - (eff_angle / 90.0))
        right_vol = min(1.0, 1.0 + (eff_angle / 90.0))
        
        # Safety clamp
        left_vol = max(0.0, min(1.0, left_vol))
        right_vol = max(0.0, min(1.0, right_vol))
        
        # Apply to Windows Volume (Channels: 0=Left, 1=Right)
        # Note: SetChannelVolumeLevelScalar takes a float 0.0 to 1.0
        volume.SetChannelVolumeLevelScalar(0, left_vol, None)
        volume.SetChannelVolumeLevelScalar(1, right_vol, None)
        
        # print(f"\rYaw: {yaw:5.1f} | Src: {eff_angle:5.1f} | L: {left_vol:.2f} R: {right_vol:.2f}", end="")

    def on_press(key):
        if key == keyboard.Key.left:
            current_keys.add('left')
        elif key == keyboard.Key.right:
            current_keys.add('right')
        elif key == keyboard.Key.esc:
            return False # Stop listener

    def on_release(key):
        if key == keyboard.Key.left:
            if 'left' in current_keys: current_keys.remove('left')
        elif key == keyboard.Key.right:
            if 'right' in current_keys: current_keys.remove('right')

    # Start Keyboard Listener in non-blocking way
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    print("Running... (Press ESC to stop)")
    
    try:
        while listener.is_alive():
            # Update Yaw based on keys
            step = 2.0
            if 'left' in current_keys:
                yaw -= step
            if 'right' in current_keys:
                yaw += step
                
            # Clamp yaw to -90 to 90 for this demo (can't look behind easily with just stereo panning)
            if yaw > 90: yaw = 90
            if yaw < -90: yaw = -90
            
            update_audio()
            time.sleep(0.02) # 50Hz update rate
            
    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopping...")
        # Reset Volume to 100% on both channels before exit
        volume.SetChannelVolumeLevelScalar(0, 1.0, None)
        volume.SetChannelVolumeLevelScalar(1, 1.0, None)
        print("Volume Reset to 100%. Bye!")

if __name__ == "__main__":
    main()
