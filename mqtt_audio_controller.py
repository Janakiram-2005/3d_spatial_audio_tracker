import time
import math
import json
import paho.mqtt.client as mqtt
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# --- CONFIGURATION ---
MQTT_BROKER = "127.0.0.1"  # Replace with the Node-RED/Broker IP if hosted elsewhere
MQTT_PORT = 1883
AUDIO_TOPIC = "audio/processed_orientation"  # Node-RED publishes here after processing
CMD_TOPIC = "cmd/python_status"

# We start with the original sensitivity values, but node-red might override them later.
PITCH_MIN = -20.0
PITCH_MAX = 20.0
ROLL_THRESHOLD = 5.0
ROLL_MAX = 35.0
# ---------------------

volume_interface = None

def map_value(value, in_min, in_max, out_min, out_max):
    """Maps a value from one range to another and clamps it."""
    value = max(min(value, max(in_min, in_max)), min(in_min, in_max))
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def setup_windows_audio():
    """Initializes the pycaw library to control Windows Master Volume."""
    devices = AudioUtilities.GetSpeakers()
    return devices.EndpointVolume

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT Broker!")
        client.subscribe(AUDIO_TOPIC)
        print(f"Subscribed to topic: {AUDIO_TOPIC}")
        client.publish(CMD_TOPIC, "Audio Controller Online")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """Callback when a message is received from Node-RED"""
    global volume_interface
    
    if not volume_interface:
        return

    try:
        # Node-RED should send JSON: {"pitch": 12.5, "roll": 2.1}
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        # Optionally allow Node-RED to inject sensitivity updates dynamically
        pitch_min = data.get("pitch_min", PITCH_MIN)
        pitch_max = data.get("pitch_max", PITCH_MAX)
        roll_thresh = data.get("roll_threshold", ROLL_THRESHOLD)
        roll_max = data.get("roll_max", ROLL_MAX)

        pitch = float(data.get("pitch", 0.0))
        roll = float(data.get("roll", 0.0))

        # 1. Map Pitch to Master Volume (0.0 to 1.0)
        overall_vol = map_value(pitch, pitch_min, pitch_max, 0.0, 1.0)
        volume_interface.SetMasterVolumeLevelScalar(overall_vol, None)

        # 2. Map Roll to Ear Balance (Panning)
        left_vol = overall_vol
        right_vol = overall_vol

        if roll < -roll_thresh:
            right_vol = overall_vol * map_value(roll, -roll_thresh, -roll_max, 1.0, 0.0)
        elif roll > roll_thresh:
            left_vol = overall_vol * map_value(roll, roll_thresh, roll_max, 1.0, 0.0)

        volume_interface.SetChannelVolumeLevelScalar(0, left_vol, None)
        volume_interface.SetChannelVolumeLevelScalar(1, right_vol, None)

        vol_percent = int(overall_vol * 100)
        print(f"MQTT Pitch: {pitch:6.1f}° -> Vol: {vol_percent}% | Roll: {roll:6.1f}° -> Balance [L:{left_vol:.2f}, R:{right_vol:.2f}]        ", end='\r')

    except json.JSONDecodeError:
        print(f"Received malformed JSON on {msg.topic}: {msg.payload}")
    except Exception as e:
        print(f"Error processing message: {e}")

def main():
    global volume_interface
    print("Connecting to Windows Audio System...")
    try:
        volume_interface = setup_windows_audio()
    except Exception as e:
        print(f"Failed to connect to Windows Audio: {e}")
        return
    
    print(f"Connecting to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}...")
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"Failed to connect to MQTT Broker: {e}")
        print("Make sure you have an MQTT Broker (like Mosquitto) running!")
        return

    print("Listening for MQTT audio commands (Press Ctrl+C to exit)...\n")
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nExiting...")
        client.disconnect()

if __name__ == "__main__":
    main()
