from openal import *
import math
import time
import os

def main():
    if not os.path.exists("sound.wav"):
        print("Error: sound.wav not found! Run generate_sound.py first.")
        return

    print("Initializing OpenAL...")
    try:
        # Initialize OpenAL
        oalInit()
    except Exception as e:
        print(f"Failed to initialize OpenAL: {e}")
        print("Make sure OpenAL Soft is installed or the DLL is in the path.")
        return

    # Load sound
    print("Loading sound.wav...")
    try:
        source = oalOpen("sound.wav")
        source.set_looping(True)

        # Place sound source in front
        source.set_position([0, 0, -2])
        source.play()
    except Exception as e:
        print(f"Error checking sound or source: {e}")
        oalQuit()
        return

    # Get Listener
    listener = oalGetListener()

    yaw = 0.0
    print("Playing sound. Moving listener automatically...")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            yaw += 0.5  # simulate head turning
            rad = math.radians(yaw)

            # Calculate forward vector
            fx = math.sin(rad)
            fz = -math.cos(rad)

            # Listener orientation: forward + up
            # forward vector (fx, 0, fz), up vector (0, 1, 0)
            listener.set_orientation([fx, 0, fz, 0, 1, 0])

            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\nStopping...")
        source.stop()
        oalQuit()

if __name__ == "__main__":
    main()
