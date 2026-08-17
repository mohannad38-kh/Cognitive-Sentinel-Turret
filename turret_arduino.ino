#include <Servo.h>
#include <ArduinoJson.h>

const int SERVO_PIN = 9;
const int LASER_PIN = 8;
const int TRIG_PIN = 5;
const int ECHO_PIN = 6;
const int VIB_PIN = 7;
const int SOUND_PIN = A0;

Servo turretServo;

int currentAngle = 90;
bool manualLaser = false;
bool dangerState = false;

long readUltrasonic() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return 400;
  return duration * 0.034 / 2;
}

void setup() {
  Serial.begin(115200);
  turretServo.attach(SERVO_PIN);
  turretServo.write(currentAngle);
  
  pinMode(LASER_PIN, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(VIB_PIN, INPUT);
  digitalWrite(LASER_PIN, LOW);
}

void loop() {
  long distance = readUltrasonic();
  bool vibration = digitalRead(VIB_PIN) == HIGH;
  int soundVal = analogRead(SOUND_PIN);
  bool loudSound = soundVal > 600;

  if (distance <= 20 || vibration || loudSound) {
    dangerState = true;
    digitalWrite(LASER_PIN, HIGH);
    turretServo.write(90); 
  } else {
    dangerState = false;
    digitalWrite(LASER_PIN, manualLaser ? HIGH : LOW);
  }

  if (Serial.available() > 0) {
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, Serial);
    
    if (!error && !dangerState) {
      if (doc.containsKey("servo")) {
        currentAngle = doc["servo"];
        turretServo.write(currentAngle);
      }
      if (doc.containsKey("laser")) {
        manualLaser = doc["laser"];
      }
    }
  }

  StaticJsonDocument<200> outDoc;
  outDoc["distance"] = distance;
  outDoc["danger"] = dangerState;
  serializeJson(outDoc, Serial);
  Serial.println();

  delay(50);
}
