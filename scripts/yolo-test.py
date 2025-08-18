from ultralytics import YOLO
import cv2

# Load YOLOv8 pretrained model
model = YOLO("yolov8n.pt")  # 'n' = nano, fastest model

# Start webcam
cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("Error: Can't open camera")
    exit()

while True:
    ret, frame = cam.read()
    if not ret:
        break

    # Run YOLO detection
    results = model(frame, show=True)
    for r in results:
        for c in r.boxes.cls:
            print(model.names[int(c)])

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
