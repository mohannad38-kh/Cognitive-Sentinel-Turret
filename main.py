import cv2
import serial
import json
import threading
import time
from cvzone.HandTrackingModule import HandDetector

COM_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

try:
    arduino = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2)
    connected = True
    print(f"تم الاتصال بالأردوينو على {COM_PORT}")
except Exception as e:
    connected = False
    print(f"فشل الاتصال بالأردوينو: {e}")

servo_angle = 90
distance = 0
danger = False
manual_laser = False

def send_to_arduino(data):
    if connected:
        try:
            msg = json.dumps(data) + '\n'
            arduino.write(msg.encode('utf-8'))
        except Exception:
            pass

def read_from_arduino():
    global distance, danger
    while True:
        if connected and arduino.in_waiting > 0:
            try:
                line = arduino.readline().decode('utf-8').strip()
                if line:
                    data = json.loads(line)
                    distance = data.get("distance", 0)
                    danger = data.get("danger", False)
            except Exception:
                pass
        time.sleep(0.05)

threading.Thread(target=read_from_arduino, daemon=True).start()

camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

detector = HandDetector(detectionCon=0.7, maxHands=1)

while True:
    ret, frame = camera.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    height, width, _ = frame.shape

    hands, frame = detector.findHands(frame, flipType=False)

    if hands and not danger:
        hand = hands[0]
        lmList = hand["lmList"]
        wrist = lmList[0]
        
        x_pos = wrist[0]
        new_angle = int((x_pos / width) * 180)
        new_angle = max(0, min(180, new_angle))

        if abs(new_angle - servo_angle) >= 3:
            servo_angle = new_angle
            send_to_arduino({"servo": servo_angle})

        fingers = detector.fingersUp(hand)
        if fingers == [1, 1, 1, 1, 1]:  
            if not manual_laser:
                manual_laser = True
                send_to_arduino({"laser": True})
        elif fingers == [0, 0, 0, 0, 0]: 
            if manual_laser:
                manual_laser = False
                send_to_arduino({"laser": False})

    status_str = "DANGER OVERRIDE ACTIVE!" if danger else "MANUAL CONTROL (HAND TRACKING)"
    status_color = (0, 0, 255) if danger else (0, 255, 0)

    cv2.putText(frame, f"Status: {status_str}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    cv2.putText(frame, f"Distance: {distance:.1f} cm", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"Servo Angle: {servo_angle} deg", (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.imshow("Cognitive Sentinel Turret", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()
if connected:
    arduino.close()
