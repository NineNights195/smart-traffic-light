import cv2
import numpy as np
import time

def simulate_traffic_light():
    # Create background
    img = np.zeros((400, 200, 3), dtype=np.uint8)

    # Lights positions
    positions = [(100, 70), (100, 170), (100, 270)]
    colors = [(0,0,255), (0,255,255), (0,255,0)]  # Red, Yellow, Green

    # States (logical order) and durations
    states = ["RED", "GREEN", "YELLOW"]       # Light cycle order (Red -> Green -> Yellow then back to Red)
    times = [10, 10, 4]

    # Map each logical state index to the index of the light (position) that should light up.
    # This keeps the UI layout the same: top=red(0), middle=yellow(1), bottom=green(2).
    # state_to_light_index[0] -> which light (0..2) should be active for states[0]
    state_to_light_index = [0, 2, 1]         # CHANGED: maps RED->pos0, GREEN->pos2 (bottom), YELLOW->pos1 (middle)

    state = 0
    while True:
        # Reset background
        img[:] = (0,0,0)

        # Draw lights
        active_light = state_to_light_index[state]   # use mapping to choose which circle is active
        for i, pos in enumerate(positions):
            if i == active_light:  # active
                cv2.circle(img, pos, 50, colors[i], -1)
            else:  # inactive
                cv2.circle(img, pos, 50, (50, 50, 50), -1)

        # Timer
        start = time.time()
        while time.time() - start < times[state]:
            cv2.imshow("Traffic Light", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                return

        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            return

        # Next state
        state = (state + 1) % len(states)  # loop

# Run the simulate
simulate_traffic_light()
