import pygame
from openal import *
import math
import os
import sys

def main():
    # --- Setup Pygame for Input ---
    pygame.init()
    screen = pygame.display.set_mode((600, 300))
    pygame.display.set_caption("Full Spatial Audio Sim (Arrows to Move Head)")
    font = pygame.font.Font(None, 36)
    
    # --- File Selection ---
    import tkinter as tk
    from tkinter import filedialog
    
    # Hidden root window for dialog
    root = tk.Tk()
    root.withdraw()
    
    print("Opening file selector...")
    selected_file = filedialog.askopenfilename(
        title="Select an Audio File (WAV)",
        filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
    )
    root.destroy()
    
    sound_path = "sound.wav"
    if selected_file:
        print(f"User selected: {selected_file}")
        sound_path = selected_file
    else:
        print("No file selected. Using default 'sound.wav'")

    # --- Setup OpenAL for Audio ---
    if not os.path.exists(sound_path):
        print(f"Error: {sound_path} not found! Run generate_sound.py first or pick a valid file.")
        pygame.quit()
        return

    print("Initializing OpenAL...")
    try:
        oalInit()
        # Verify device
        device = oalGetDevice()
        ctx = oalGetContext()
        dev_name = alcGetString(device, ALC_DEVICE_SPECIFIER)
        print(f"✅ Audio Device Opened: {dev_name}")
        
    except Exception as e:
        print(f"Failed to initialize OpenAL: {e}")
        print("Make sure OpenAL Soft is installed or the DLL is in your path/system.")
        pygame.quit()
        return

    try:
        source = oalOpen(sound_path)
        source.set_looping(True)
        source.set_position([0, 0, -2]) # Sound is 2 units in front
        source.play()
    except Exception as e:
        print(f"Failed to load or play sound: {e}")
        oalQuit()
        pygame.quit()
        return

    # Get Listener
    listener = oalGetListener()

    # --- Variables ---
    yaw = 0.0
    pitch = 0.0
    
    running = True
    clock = pygame.time.Clock()

    print("Simulation Started.")
    print("Use LEFT/RIGHT for Yaw (Turning Head)")
    print("Use UP/DOWN for Pitch (Looking Up/Down)")

    while running:
        # 1. Input Processing
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        
        # Sensitivity
        turn_speed = 2.0 

        if keys[pygame.K_LEFT]:
            yaw -= turn_speed
        if keys[pygame.K_RIGHT]:
            yaw += turn_speed
        if keys[pygame.K_UP]:
            pitch += turn_speed
        if keys[pygame.K_DOWN]:
            pitch -= turn_speed

        # 2. Math / Orientation Calculation
        # Convert to radians
        rad_yaw = math.radians(yaw)
        rad_pitch = math.radians(pitch)

        # Calculate Forward Vector
        # x = cos(pitch) * sin(yaw)
        # y = sin(pitch)
        # z = -cos(pitch) * cos(yaw)
        fx = math.cos(rad_pitch) * math.sin(rad_yaw)
        fy = math.sin(rad_pitch)
        fz = -math.cos(rad_pitch) * math.cos(rad_yaw)
        
        # Up Vector (Simplified for small pitch, strict FPS style usually needs proper up vector calculation)
        ux, uy, uz = 0, 1, 0

        # 3. Update Audio Listener
        listener.set_orientation([fx, fy, fz, ux, uy, uz])

        # 4. Visual Feedback
        screen.fill((30, 30, 30))
        
        info_lines = [
            f"Yaw: {yaw:.1f}",
            f"Pitch: {pitch:.1f}",
            f"File: {os.path.basename(sound_path)}",
            "Sound Source: Fixed at (0, 0, -2)"
        ]
        
        for i, line in enumerate(info_lines):
            text = font.render(line, True, (200, 200, 200))
            screen.blit(text, (20, 20 + i * 40))

        # Draw a little "radar" or top-down view
        center_x, center_y = 450, 150
        radius = 50
        pygame.draw.circle(screen, (100, 100, 100), (center_x, center_y), radius, 2)
        
        # Draw head direction (yaw only for top-down)
        end_x = center_x + math.sin(rad_yaw) * radius
        end_y = center_y - math.cos(rad_yaw) * radius
        pygame.draw.line(screen, (0, 255, 0), (center_x, center_y), (end_x, end_y), 3)

        pygame.display.flip()
        clock.tick(60) # 60 FPS

    # Cleanup
    source.stop()
    oalQuit()
    pygame.quit()

if __name__ == "__main__":
    main()
