import cv2
import numpy as np
from ultralytics import YOLO
import time
import os

# ---------------- Configuration ----------------
CAM_INDEX = 2
MODEL_PATH = "models/yolov8n.pt"
CONFIDENCE = 0.25
IMG_SZ = 640
YELLOW_DURATION = 2   # seconds for Green -> Yellow -> Red
GREEN_DURATION = 4    # minimum seconds that green must stay before it can switch
FLASH_DURATION = 3    # seconds for flashing when Red -> Green
NO_PERSON_CONFIRM = 2  # seconds of continuous no-person required before switching RED -> FLASHING -> GREEN
PERSON_CONFIRM = 2     # seconds of continuous person detection required before switching GREEN -> YELLOW
# ------------------------------------------------

# Ensure YOLO weights exist (auto-download if missing)
if not os.path.exists(MODEL_PATH):
    model = YOLO("models/yolov8n.pt")
else:
    model = YOLO(MODEL_PATH)

vehicle_classes = [1, 2, 3, 5, 7]
target_classes = [0] + vehicle_classes  # 0 = person

cam = cv2.VideoCapture(CAM_INDEX)
if not cam.isOpened():
    print(f"Error: Can't open camera index {CAM_INDEX}")
    exit()

# ---------- UI Drawing Helpers ----------
def draw_traffic_light(canvas, state):
    x, y, w, h = 50, 50, 120, 320
    cv2.rectangle(canvas, (x, y), (x + w, y + h), (30, 30, 30), -1)

    cx = x + w // 2
    cy_red, cy_yellow, cy_green = y + 60, y + 160, y + 260

    cv2.circle(canvas, (cx, cy_red), 40, (50, 50, 50), -1)
    cv2.circle(canvas, (cx, cy_yellow), 40, (50, 50, 50), -1)
    cv2.circle(canvas, (cx, cy_green), 40, (50, 50, 50), -1)

    if state == "RED":
        cv2.circle(canvas, (cx, cy_red), 40, (0, 0, 255), -1)
    elif state == "YELLOW":
        cv2.circle(canvas, (cx, cy_yellow), 40, (0, 255, 255), -1)
    elif state == "GREEN":
        cv2.circle(canvas, (cx, cy_green), 40, (0, 255, 0), -1)

    cv2.putText(canvas, f"TRAFFIC: {state}", (30, y + h + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

def draw_pedestrian_light(canvas, state):
    x, y, w, h = 250, 100, 220, 120
    cv2.rectangle(canvas, (x, y), (x + w, y + h), (30, 30, 30), -1)

    left_center = (x + 60, y + h // 2)
    right_center = (x + 160, y + h // 2)

    cv2.circle(canvas, left_center, 40, (50, 50, 50), -1)
    cv2.circle(canvas, right_center, 40, (50, 50, 50), -1)

    if state == "STOP":
        cv2.circle(canvas, left_center, 40, (0, 0, 255), -1)
        cv2.putText(canvas, "STOP", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,255), 3)
    elif state == "WALK":
        cv2.circle(canvas, right_center, 40, (0, 255, 0), -1)
        cv2.putText(canvas, "WALK", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 3)
# ---------------------------------------

print("Starting Smart Traffic Light (state machine). Press 'q' to quit.")

# ---- State Machine Variables ----
traffic_state = "GREEN"
pedestrian_state = "STOP"
phase_start = time.time()
last_switch = 0
no_person_start = None     # timer to confirm continuous absence of people (RED -> GREEN)
person_detect_start = None # timer to confirm continuous presence of people (GREEN -> YELLOW)
# ----------------------------------

while True:
    ret, frame = cam.read()
    if not ret:
        break

    results = model(frame, imgsz=IMG_SZ, conf=CONFIDENCE, classes=target_classes)
    annotated = results[0].plot()

    person_count, vehicle_count = 0, 0
    for r in results:
        if hasattr(r.boxes, "cls") and r.boxes.cls is not None:
            for c in r.boxes.cls:
                cid = int(c)
                if cid == 0:
                    person_count += 1
                elif cid in vehicle_classes:
                    vehicle_count += 1

    # ----------- Traffic Light State Machine -----------
    now = time.time()

    if traffic_state == "GREEN":
        # vehicles get green, pedestrians STOP
        pedestrian_state = "STOP"

        # Confirm person presence for PERSON_CONFIRM seconds before switching,
        # and only if minimum GREEN_DURATION has passed.
        if person_count > 0:
            if person_detect_start is None:
                person_detect_start = now  # start presence confirmation timer
            else:
                if (now - person_detect_start >= PERSON_CONFIRM) and (now - phase_start >= GREEN_DURATION):
                    traffic_state = "YELLOW"
                    phase_start = now
                    # reset timers
                    person_detect_start = None
                    no_person_start = None
        else:
            # no person now -> reset the presence confirmation timer
            person_detect_start = None

    elif traffic_state == "YELLOW":
        pedestrian_state = "STOP"
        # during yellow, presence/presence timer not needed; wait fixed yellow duration
        if now - phase_start >= YELLOW_DURATION:
            traffic_state = "RED"
            pedestrian_state = "WALK"
            phase_start = now
            # reset timers
            no_person_start = None
            person_detect_start = None

    elif traffic_state == "RED":
        # pedestrians WALK while RED is active
        pedestrian_state = "WALK"
        # start confirmation timer when no persons detected
        if person_count == 0:
            if no_person_start is None:
                no_person_start = now  # start confirmation timer
            else:
                # if absence persisted long enough, transition to FLASHING -> then GREEN
                if now - no_person_start >= NO_PERSON_CONFIRM:
                    traffic_state = "FLASHING"
                    phase_start = now
                    no_person_start = None
                    person_detect_start = None
        else:
            # someone still detected — reset the no-person timer
            no_person_start = None

    elif traffic_state == "FLASHING":
        # flashing alternates pedestrian STOP/WALK quickly
        if int((now - phase_start) * 2) % 2 == 0:
            pedestrian_state = "STOP"
        else:
            pedestrian_state = "WALK"
        if now - phase_start >= FLASH_DURATION:
            traffic_state = "GREEN"
            pedestrian_state = "STOP"
            phase_start = now
            no_person_start = None
            person_detect_start = None
    # ---------------------------------------------------

    # --- Create UI canvas ---
    ui = np.zeros((annotated.shape[0], 600, 3), dtype=np.uint8)
    draw_traffic_light(ui, traffic_state if traffic_state != "FLASHING" else "RED")
    draw_pedestrian_light(ui, pedestrian_state)

    cv2.putText(ui, f"Persons: {person_count}", (30, 300),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
    cv2.putText(ui, f"Vehicles: {vehicle_count}", (30, 340),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

    combined = np.hstack((annotated, ui))
    cv2.imshow("Smart Traffic Light", combined)

    if now - last_switch > 1:
        # show debug info, include timers if active
        pd_timer = None if person_detect_start is None else round(now - person_detect_start, 1)
        np_timer = None if no_person_start is None else round(now - no_person_start, 1)
        print(f"Traffic: {traffic_state}, Pedestrian: {pedestrian_state} "
              f"(Persons: {person_count}, Vehicles: {vehicle_count}), "
              f"person_detect_timer: {pd_timer}s, no_person_timer: {np_timer}s")
        last_switch = now

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()
