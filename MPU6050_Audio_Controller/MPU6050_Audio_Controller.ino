#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// Include ESP32 Bluetooth Classic Library
#include "BluetoothSerial.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please enable it in your IDE.
#endif

BluetoothSerial SerialBT;
Adafruit_MPU6050 mpu;

// Offsets for calibration
float pitch_offset = 0.0;
float roll_offset = 0.0;

void setup() {
  Serial.begin(115200);
  
  // Initialize Bluetooth with a recognizable name
  SerialBT.begin("MPU6050_Audio_Tracker"); 
  Serial.println("Bluetooth Started! Ready to pair.");
  
  delay(1000);   // allow serial monitor to connect

  Wire.begin(21, 22);   // SDA = 21, SCL = 22 (ESP32 defaults usually)

  if (!mpu.begin()) {
    while (1) {
      Serial.println("MPU6050 not found! Check wiring.");
      delay(1000);
    }
  }

  // --- Automatic Calibration ---
  // Wait a moment for sensor to stabilize
  delay(500);
  
  float sum_pitch = 0.0;
  float sum_roll = 0.0;
  int num_readings = 50;

  for (int i = 0; i < num_readings; i++) {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
    sum_roll  += atan2(a.acceleration.y, a.acceleration.z) * 180.0 / PI;
    sum_pitch += atan2(-a.acceleration.x, sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z)) * 180.0 / PI;
    delay(20);
  }

  pitch_offset = sum_pitch / num_readings;
  roll_offset = sum_roll / num_readings;
  // -----------------------------
}

void loop() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // 1. Calculate Raw Pitch and Roll
  float raw_roll  = atan2(a.acceleration.y, a.acceleration.z) * 180.0 / PI;
  float raw_pitch = atan2(-a.acceleration.x, sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z)) * 180.0 / PI;

  // 2. Apply offsets so it always starts at 0,0
  float pitch = raw_pitch - pitch_offset;
  float roll = raw_roll - roll_offset;

  // 3. Print over USB Serial
  Serial.print(pitch);
  Serial.print(",");
  Serial.println(roll);

  // 4. Print exclusively as "pitch,roll" over Bluetooth Serial
  SerialBT.print(pitch);
  SerialBT.print(",");
  SerialBT.println(roll);

  // Send data at ~20-25Hz (40ms) for smooth spatial audio transitions without overloading python
  delay(40);
}

