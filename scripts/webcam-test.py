import cv2

cam = cv2.VideoCapture(0)  # 0 is default webcam
if not cam.isOpened():
    print("Error: Can't open camera")
    exit()

while True:
    ret, frame = cam.read()
    if not ret:
        print("Error: Can't receive frame. Exiting...")
        break
    cv2.imshow("Webcam test", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
