import cv2
import numpy as np
import time

def simulate_pedestrian_light():
    # Create a blank window
    width, height = 600, 400
    window = np.zeros((height, width, 3), dtype=np.uint8)

    # State and durations control
    states = [("STOP", (0, 0, 255)),  # Red
              ("WALK", (0, 255, 0))]  # Green
    durations = [5, 8]
    current_state = 0
    last_switch = time.time()

    while True:
        # Check if it's time to switch state
        if time.time() - last_switch > durations[current_state]:
            current_state = (current_state + 1) % len(states)
            last_switch = time.time()

        # Get current state
        text, color = states[current_state]

        # Draw UI
        frame = window.copy()
        cv2.rectangle(frame, (100, 100), (500, 300), (50, 50, 50), -1)  # horizontal signal box

        if text == "STOP":
            cv2.circle(frame, (200, 200), 80, color, -1)  # left red light
        elif text == "WALK":
            cv2.circle(frame, (400, 200), 80, color, -1)  # right green light

        # Add label
        cv2.putText(frame, text, (20, 380), cv2.FONT_HERSHEY_SIMPLEX,
                    1, color, 2, cv2.LINE_AA)

        cv2.imshow("Pedestrian Traffic Light", frame)

        # Exit with Q
        if cv2.waitKey(100) & 0xFF == ord("q"):
            cv2.destroyAllWindows()
            break

# Run the simulate
simulate_pedestrian_light()