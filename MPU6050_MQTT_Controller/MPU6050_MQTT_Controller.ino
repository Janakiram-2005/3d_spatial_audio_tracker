#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <WiFi.h>
#include <PubSubClient.h>

// --- CONFIGURATION ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "192.168.1.100";  // Node-RED / Broker IP

Adafruit_MPU6050 mpu;
WiFiClient espClient;
PubSubClient client(espClient);

float pitch_offset = 0.0;
float roll_offset = 0.0;

unsigned long lastMsg = 0;
const int MSG_INTERVAL = 50;  // 20hz update rate

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messageTemp;
  
  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    messageTemp += (char)message[i];
  }
  Serial.println();

  // If we receive a command to recalibrate
  if (String(topic) == "cmd/recalibrate") {
    Serial.println("Recalibrating origin...");
    recalibrate();
  }
}

void recalibrate() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  
  float raw_roll  = atan2(a.acceleration.y, a.acceleration.z) * 180.0 / PI;
  float raw_pitch = atan2(-a.acceleration.x, sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z)) * 180.0 / PI;
  
  pitch_offset = raw_pitch;
  roll_offset = raw_roll;
  Serial.println("Recalibration complete.");
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect("ESP32_Audio_Controller")) {
      Serial.println("connected");
      // Resubscribe
      client.subscribe("cmd/recalibrate");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("Starting MPU6050 MQTT...");
  Wire.begin(21, 22);

  if (!mpu.begin()) {
    Serial.println("MPU6050 not found! Check wiring.");
    while (1);
  }
  Serial.println("MPU6050 Ready");

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();
  if (now - lastMsg > MSG_INTERVAL) {
    lastMsg = now;
    
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    float raw_roll  = atan2(a.acceleration.y, a.acceleration.z) * 180.0 / PI;
    float raw_pitch = atan2(-a.acceleration.x, sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z)) * 180.0 / PI;

    // Apply offsets
    float pitch = raw_pitch - pitch_offset;
    float roll = raw_roll - roll_offset;

    // Create JSON payload manually (to avoid heavy ArduinoJson library if possible)
    String payload = "{";
    payload += "\"pitch\":"; payload += String(pitch, 2); payload += ",";
    payload += "\"roll\":"; payload += String(roll, 2);
    payload += "}";

    // Publish
    client.publish("sensor/raw_orientation", payload.c_str());
    
    // Also print to serial for local debugging
    // Serial.println(payload);
  }
}
