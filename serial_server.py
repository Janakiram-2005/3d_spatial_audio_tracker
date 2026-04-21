import time
import math
import json
import threading
import serial
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

app = FastAPI()

# --- SHARED STATE ---
settings = {
    "com_port": "COM3",
    "baud_rate": 115200,
    "pitch_min": -20.0,
    "pitch_max": 20.0,
    "pitch_deadzone": 2.0,
    "roll_max": 35.0,
    "roll_deadzone": 5.0,
    "max_system_volume": 50.0,  # Cap at 50% system volume
    "audio_enabled": True
}

state = {
    "raw_pitch": 0.0,
    "raw_roll": 0.0,
    "offset_pitch": 0.0,
    "offset_roll": 0.0,
    "master_volume": 0.0,
    "left_balance": 1.0,
    "right_balance": 1.0,
    "smoothed_vol": 0.0,
    "smoothed_left": 1.0,
    "smoothed_right": 1.0,
    "status": "Disconnected"
}

volume_interface = None
serial_conn = None
serial_thread_running = False

# --- UTILS WITH DEADZONE ---
def map_value(value, in_min, in_max, out_min, out_max):
    value = max(min(value, max(in_min, in_max)), min(in_min, in_max))
    # Protect against div by zero
    if in_max == in_min: return out_min
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def apply_deadzone_and_map(val, deadzone, max_val):
    """Maps value outside of deadzone linearly to 1.0 or -1.0"""
    direction = 1 if val >= 0 else -1
    abs_val = abs(val)

    if abs_val <= deadzone:
        return 0.0
    
    # Map range [deadzone, max_val] to [0.0, 1.0]
    mapped = map_value(abs_val, deadzone, max_val, 0.0, 1.0)
    return mapped * direction

# --- WINDOWS AUDIO & SMOOTHING THREAD ---
def audio_loop():
    global volume_interface, state, settings, serial_thread_running
    import comtypes
    comtypes.CoInitialize()

    tick_count = 0
    
    # Initialize targets to avoid jump
    target_vol = 0.0
    target_left = 1.0
    target_right = 1.0

    while serial_thread_running:
        # Every 2 seconds (100 ticks @ 50hz), refresh the default audio device
        # This handles dynamic switching (e.g. plugging in bluetooth headphones)
        if tick_count % 100 == 0:
            try:
                devices = AudioUtilities.GetSpeakers()
                volume_interface = devices.EndpointVolume
            except Exception as e:
                print(f"[Audio Refresh Error] {e}")
        tick_count += 1

        if settings["audio_enabled"] and volume_interface:
            pitch = state["raw_pitch"]
            roll = state["raw_roll"]

            # --- PITCH -> MASTER VOLUME ---
            pitch_val = pitch
            if abs(pitch) < settings["pitch_deadzone"]:
                pitch_val = 0.0

            max_vol = settings["max_system_volume"] / 100.0
            target_vol = map_value(pitch_val, settings["pitch_min"], settings["pitch_max"], 0.0, max_vol)
            
            # --- ROLL -> EQUAL POWER PANNING ---
            pan_factor = apply_deadzone_and_map(roll, settings["roll_deadzone"], settings["roll_max"])
            p_norm = (pan_factor + 1.0) / 2.0
            target_left = math.cos(p_norm * math.pi / 2.0)
            target_right = math.sin(p_norm * math.pi / 2.0)

            # --- EXPONENTIAL MOVING AVERAGE (EMA) SMOOTHING ---
            # Smoothing is now processed exactly 50 times a second, completely eliminating Bluetooth jitter
            state["smoothed_vol"] = state["smoothed_vol"] * 0.85 + target_vol * 0.15
            state["smoothed_left"] = state["smoothed_left"] * 0.85 + target_left * 0.15
            state["smoothed_right"] = state["smoothed_right"] * 0.85 + target_right * 0.15

            # Clamp boundaries for COM APIs
            final_vol = max(0.001, min(1.0, state["smoothed_vol"]))
            final_l = max(0.001, min(1.0, state["smoothed_left"]))
            final_r = max(0.001, min(1.0, state["smoothed_right"]))

            try:
                # Set audio
                volume_interface.SetMasterVolumeLevelScalar(final_vol, None)
                volume_interface.SetChannelVolumeLevelScalar(0, final_l, None)
                volume_interface.SetChannelVolumeLevelScalar(1, final_r, None)
            except Exception as com_err:
                # Ignore random COM dropouts during device switches
                pass

            # Update UI State safely
            state["master_volume"] = final_vol
            state["left_balance"] = final_l
            state["right_balance"] = final_r

        time.sleep(0.02) # Exactly 50Hz

# --- SERIAL DATA THREAD ---
def serial_loop():
    global serial_conn, state, settings, serial_thread_running
    
    while serial_thread_running:
        if not serial_conn:
            try:
                state["status"] = f"Connecting to {settings['com_port']}..."
                serial_conn = serial.Serial(settings["com_port"], settings["baud_rate"], timeout=1)
                time.sleep(1) # Let serial stabilize
                state["status"] = f"Connected to {settings['com_port']}"
                if serial_conn.in_waiting:
                    serial_conn.reset_input_buffer()
            except Exception as e:
                state["status"] = f"Error: {e}"
                time.sleep(2)
                continue

        try:
            line = serial_conn.readline().decode('utf-8', errors='ignore').strip()
            if line:
                data = line.split(',')
                if len(data) == 2:
                    try:
                        raw_p = float(data[0])
                        raw_r = float(data[1])
                    except ValueError:
                        continue
                    
                    # Store latest value for the Audio Thread
                    state["raw_pitch"] = raw_p - state["offset_pitch"]
                    state["raw_roll"] = raw_r - state["offset_roll"]

        except serial.SerialException as e:
            state["status"] = f"Serial Error: {e}"
            if serial_conn:
                serial_conn.close()
                serial_conn = None
            time.sleep(1)
        except Exception as e:
            print(f"[Serial Loop Error] {e}")

def start_threads():
    global serial_thread_running
    if not serial_thread_running:
        serial_thread_running = True
        threading.Thread(target=serial_loop, daemon=True).start()
        threading.Thread(target=audio_loop, daemon=True).start()

# --- FASTAPI APP ---

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# Websocket endpoint for real-time bidirection comms
manager: list[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    manager.append(websocket)
    # Send initial settings
    await websocket.send_json({"type": "settings", "data": settings})
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message["type"] == "update_settings":
                new_set = message["data"]
                # Update global settings
                settings.update(new_set)
                
                # Check for COM port change
                global serial_conn
                if serial_conn and serial_conn.port != settings["com_port"]:
                    serial_conn.close()
                    serial_conn = None
                    
                # Broadcast back to all clients
                for conn in manager:
                    await conn.send_json({"type": "settings", "data": settings})
            
            elif message["type"] == "recalibrate":
                # Add the current relative position to the absolute offset
                state["offset_pitch"] += state["raw_pitch"]
                state["offset_roll"] += state["raw_roll"]
                print("Recalibrated Origin.")
    except WebSocketDisconnect:
        manager.remove(websocket)

async def broadcast_state():
    while True:
        if len(manager) > 0:
            payload = {"type": "state", "data": state}
            broken_conn = []
            for conn in manager:
                try:
                    await conn.send_json(payload)
                except:
                    broken_conn.append(conn)
            for br in broken_conn:
                manager.remove(br)
        import asyncio
        await asyncio.sleep(0.05) # 20 Hz update rate to UI is more than enough

@app.on_event("startup")
async def startup_event():
    start_threads()
    import asyncio
    asyncio.create_task(broadcast_state())

if __name__ == "__main__":
    uvicorn.run("serial_server:app", host="127.0.0.1", port=8000, log_level="info")
