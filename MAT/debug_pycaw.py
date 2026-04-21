from pycaw.pycaw import AudioUtilities

def debug_pycaw():
    try:
        devices = AudioUtilities.GetSpeakers()
        print(f"Devices type: {type(devices)}")
        if devices:
            print(f"Dir of devices: {dir(devices)}")
        else:
            print("GetSpeakers returned None")
            
        print("-" * 20)
        all_devs = AudioUtilities.GetAllDevices()
        print(len(all_devs))
        if len(all_devs) > 0:
            d = all_devs[0]
            print(f"First device dir: {dir(d)}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_pycaw()
