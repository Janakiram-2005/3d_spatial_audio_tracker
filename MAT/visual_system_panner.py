import pygame
import time
import math
import sys
import threading
from pycaw.pycaw import AudioUtilities
from pynput import keyboard

# --- Global State ---
state = {
    "yaw": 0.0,
    "pitch": 0.0,
    "volume_master": 0.5, # Starts at 50%, updates from system
    "left_vol": 0.5,
    "right_vol": 0.5,
    "running": True
}

# --- Audio Engine (Pycaw + Logic) ---
def audio_loop():
    print("Initializing Audio Engine...")
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.EndpointVolume
    except Exception as e:
        print(f"Audio Init Failed: {e}")
        return

    # Initialize master volume from system
    current_sys_vol = interface.GetMasterVolumeLevelScalar()
    state["volume_master"] = current_sys_vol
    print(f"Initial System Volume: {int(current_sys_vol * 100)}%")

    while state["running"]:
        # Logic:
        # Panning based on Yaw
        # Attenuation based on Pitch (if looking up/down, slightly quieter?)
        
        yaw = state["yaw"]
        pitch = state["pitch"]
        master = state["volume_master"]
        
        # Clamp Angle (-90 to 90)
        eff_yaw = max(-90, min(90, -yaw)) # Invert yaw for correct L/R feel
        
        # Calculate Balance factors (Center = 1.0, 1.0)
        # Linear Panning
        # If Yaw is 0: L=1, R=1
        # If Yaw is -90 (Left): L=1, R=0
        # If Yaw is +90 (Right): L=0, R=1
        l_factor = min(1.0, 1.0 - (eff_yaw / 90.0))
        r_factor = min(1.0, 1.0 + (eff_yaw / 90.0))
        
        # Pitch Effect: Attenuate total volume if looking up/down
        # e.g., at 90 deg pitch, volume drops to 70%
        pitch_attenuation = 1.0 - (abs(pitch) / 90.0) * 0.3
        
        # Final Channel Volumes
        final_l = max(0.0, min(1.0, master * l_factor * pitch_attenuation))
        final_r = max(0.0, min(1.0, master * r_factor * pitch_attenuation))
        
        state["left_vol"] = final_l
        state["right_vol"] = final_r
        
        # Apply to Windows
        interface.SetChannelVolumeLevelScalar(0, final_l, None)
        interface.SetChannelVolumeLevelScalar(1, final_r, None)
        
        time.sleep(0.05) # 20Hz update is enough for volume

    # Restore on exit
    interface.SetChannelVolumeLevelScalar(0, master, None)
    interface.SetChannelVolumeLevelScalar(1, master, None)

# --- Input Engine (Pynput) ---
def input_loop():
    current_keys = set()

    def on_press(key):
        if key == keyboard.Key.left: current_keys.add('left')
        if key == keyboard.Key.right: current_keys.add('right')
        if key == keyboard.Key.up: current_keys.add('up')
        if key == keyboard.Key.down: current_keys.add('down')
        if not state["running"]: return False

    def on_release(key):
        if key == keyboard.Key.left: 
            if 'left' in current_keys: current_keys.remove('left')
        if key == keyboard.Key.right: 
            if 'right' in current_keys: current_keys.remove('right')
        if key == keyboard.Key.up: 
            if 'up' in current_keys: current_keys.remove('up')
        if key == keyboard.Key.down: 
            if 'down' in current_keys: current_keys.remove('down')
            
        # Volume Control: [ ]
        # We handle single press here
        try:
            if key.char == '[':
                state["volume_master"] = max(0.0, state["volume_master"] - 0.05)
            if key.char == ']':
                state["volume_master"] = min(1.0, state["volume_master"] + 0.05)
        except AttributeError:
            pass

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    while state["running"]:
        step = 1.5
        if 'left' in current_keys: state["yaw"] -= step
        if 'right' in current_keys: state["yaw"] += step
        if 'up' in current_keys: state["pitch"] += step
        if 'down' in current_keys: state["pitch"] -= step
        
        # Clamp
        if state["yaw"] > 90: state["yaw"] = 90
        if state["yaw"] < -90: state["yaw"] = -90
        if state["pitch"] > 90: state["pitch"] = 90
        if state["pitch"] < -90: state["pitch"] = -90
        
        time.sleep(0.01)

    listener.stop()

# --- Visual Engine (Pygame) ---
def main():
    pygame.init()
    # Create small window
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption("Spatial Audio Control")
    font = pygame.font.Font(None, 28)
    clock = pygame.time.Clock()

    # Start Input Thread
    t_input = threading.Thread(target=input_loop)
    t_input.daemon = True
    t_input.start()

    # Start Audio Thread
    t_audio = threading.Thread(target=audio_loop)
    t_audio.daemon = True
    t_audio.start()

    print("Visual System Panner Running...")
    print("Close the window to stop.")

    while state["running"]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state["running"] = False

        # Draw
        screen.fill((20, 20, 20))
        
        # Radar View
        cx, cy = 200, 150
        rad = 80
        
        # Horizon / Pitch circle
        pygame.draw.circle(screen, (50, 50, 50), (cx, cy), rad, 2)
        
        # Calculate Head Vector
        # Simple projection
        yaw_rad = math.radians(state["yaw"])
        pitch_rad = math.radians(state["pitch"])
        
        # End point logic:
        # Yaw rotates around center. Pitch changes length (simulating 3D look) or y-offset?
        # Let's do simple: Yaw = X, Pitch = Y
        
        # Visualize Head Direction
        # Typically looking "forward" = Up on 2D radar, or Center?
        # Let's say Center is (0,0).
        # We draw a line from center indicating direction.
        
        dx = math.sin(yaw_rad) * rad * math.cos(pitch_rad)
        dy = -math.cos(yaw_rad) * rad * math.cos(pitch_rad) - (math.sin(pitch_rad) * rad * 0.5)
        
        pygame.draw.line(screen, (0, 255, 0), (cx, cy), (cx + dx, cy + dy), 3)
        pygame.draw.circle(screen, (0, 255, 0), (int(cx + dx), int(cy + dy)), 5)

        # Labels
        lines = [
            f"Yaw: {state['yaw']:.1f}",
            f"Pitch: {state['pitch']:.1f}",
            f"Master Vol: {int(state['volume_master']*100)}% (Use [ / ])",
            f"L: {int(state['left_vol']*100)}%  R: {int(state['right_vol']*100)}%"
        ]
        
        for i, line in enumerate(lines):
            col = (200, 200, 200)
            if "L:" in line: col = (100, 200, 255)
            sf = font.render(line, True, col)
            screen.blit(sf, (10, 10 + i * 30))
            
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
