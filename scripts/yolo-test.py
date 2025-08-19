from ultralytics import YOLO
import cv2

# Load YOLOv8 pretrained model
model = YOLO("yolov8n.pt")

cam = cv2.VideoCapture(2)
if not cam.isOpened():
    print("Error: Can't open camera")
    exit()

while True:
    ret, frame = cam.read()
    if not ret:
        print("Error: Can't receive frame. Exiting...")
        break

    # Run YOLO detection
    results = model(frame)
    annotated = results[0].plot()  # draw bounding boxes
    cv2.imshow("YOLO test", annotated)
    for r in results:
        for c in r.boxes.cls:
            print(model.names[int(c)])

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
