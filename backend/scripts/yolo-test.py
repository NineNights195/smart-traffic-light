from ultralytics import YOLO
import cv2

# Load YOLOv8 pretrained model
model = YOLO("yolov8n.pt")

cam = cv2.VideoCapture(2)
if not cam.isOpened():
    print("Error: Can't open camera")
    exit()

# COCO class IDs
# 0 = person
# Vehicles: 1 = bicycle, 2 = car, 3 = motorcycle, 5 = bus, 7 = truck
vehicle_classes = [1, 2, 3, 5, 7]
target_classes = [0] + vehicle_classes  # person + vehicles

while True:
    ret, frame = cam.read()
    if not ret:
        print("Error: Can't receive frame. Exiting...")
        break

    # Run YOLO detection
    results = model(frame, classes=target_classes)

    # Draw bounding boxes
    annotated = results[0].plot()

    # Frame name
    cv2.imshow("YOLO Object Detection", annotated)

    # Count detected people and vehicles
    count = {"person": 0, "car": 0}
    for r in results:
        for c in r.boxes.cls:
            class_id = int(c)
            if class_id == 0:
                count["person"] += 1
            elif class_id in vehicle_classes:
                count["car"] += 1

    print(count)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
