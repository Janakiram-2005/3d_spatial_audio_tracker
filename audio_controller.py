import serial
import time
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# --- CONFIGURATION ---
COM_PORT = 'COM3'       # Change this to match your ESP32's COM port in Arduino IDE!
BAUD_RATE = 115200      # Make sure this matches your Arduino Serial.begin()

# Sensitivity settings (degrees) - MADE MORE SENSITIVE
PITCH_MIN = -20.0       # Tilted back 20 degrees -> Min Volume (0%)
PITCH_MAX = 20.0        # Tilted forward 20 degrees -> Max Volume (100%)

ROLL_THRESHOLD = 5.0    # Deadzone before audio panning (tilting) starts to take effect
ROLL_MAX = 35.0         # Tilted 35 degrees left/right -> Full fade to one ear
# ---------------------

def map_value(value, in_min, in_max, out_min, out_max):
    """Maps a value from one range to another and clamps it."""
    # Clamp value to the input range
    value = max(min(value, max(in_min, in_max)), min(in_min, in_max))
    # Calculate mapping
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def setup_windows_audio():
    """Initializes the pycaw library to control Windows Master Volume."""
    devices = AudioUtilities.GetSpeakers()
    return devices.EndpointVolume

def main():
    print("Connecting to Windows Audio System...")
    try:
        volume = setup_windows_audio()
    except Exception as e:
        print(f"Failed to connect to Windows Audio: {e}")
        return
    
    print(f"Connecting to ESP on {COM_PORT}...")
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Give the serial connection a moment to initialize
    except Exception as e:
        print(f"Failed to connect to {COM_PORT}. Make sure the Arduino Serial Monitor is CLOSED!")
        return

    print("Listening for sensor data...\n")

    while True:
        try:
            # Read a line from the ESP
            line = ser.readline().decode('utf-8').strip()
            
            if line:
                data = line.split(',')
                # We expect exactly 2 values now: pitch, roll
                if len(data) == 2:
                    pitch = float(data[0]) 
                    roll = float(data[1])

                    # 1. Map Pitch to Master Volume (0.0 to 1.0)
                    overall_vol = map_value(pitch, PITCH_MIN, PITCH_MAX, 0.0, 1.0)
                    volume.SetMasterVolumeLevelScalar(overall_vol, None)

                    # 2. Map Roll to Ear Balance (Panning)
                    left_vol = overall_vol
                    right_vol = overall_vol

                    if roll < -ROLL_THRESHOLD: 
                        # Tilting left: fade out the right ear
                        right_vol = overall_vol * map_value(roll, -ROLL_THRESHOLD, -ROLL_MAX, 1.0, 0.0)
                    elif roll > ROLL_THRESHOLD: 
                        # Tilting right: fade out the left ear
                        left_vol = overall_vol * map_value(roll, ROLL_THRESHOLD, ROLL_MAX, 1.0, 0.0)

                    # Apply Left (Channel 0) and Right (Channel 1) balance
                    volume.SetChannelVolumeLevelScalar(0, left_vol, None)
                    volume.SetChannelVolumeLevelScalar(1, right_vol, None)

                    # Print out what the system is doing
                    vol_percent = int(overall_vol * 100)
                    print(f"Pitch: {pitch:6.1f}° -> Vol: {vol_percent}% | "
                          f"Roll: {roll:6.1f}° -> Balance [L:{left_vol:.2f}, R:{right_vol:.2f}]        ", end='\r')

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except ValueError:
             # Ignore occasional line reading errors while parsing float
             pass
        except Exception as e:
             print(f"\nError: {e}")
             break

if __name__ == "__main__":
    main()
