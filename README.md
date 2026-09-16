# 🚦 Smart Traffic Light

AI-assisted traffic-light prototype that uses a camera feed to prioritise pedestrian safety. The current milestone is to turn the original Python proof of concept into a complete, demonstrable system: a reliable detection and control backend, a web dashboard for monitoring it, and eventually a Raspberry Pi deployment.

Built originally for **Coding Thailand 2025 – Regional Competition**.

## What works today

The Python backend:

- Reads live video from a webcam.
- Uses the YOLOv8 nano model to detect people and common vehicle classes.
- Runs a traffic-light state machine with `GREEN`, `YELLOW`, `RED`, and pedestrian-transition flashing states.
- Gives pedestrians priority: sustained person detection changes vehicle traffic from green to yellow, then red; the vehicle light returns to green only after no people are detected for a configured time.
- Shows the annotated camera feed and simulated vehicle/pedestrian lights in an OpenCV window.

The frontend is being set up with React and Vite. It is currently a starter interface, not yet connected to the detection backend.

## Project structure

```text
smart-traffic-light/
├── backend/
│   ├── main.py              # Camera, YOLO detection, and light state machine
│   ├── requirements.txt     # Python dependencies
│   └── scripts/             # Small experiments and YOLO model file
├── frontend/                # React + Vite dashboard (under development)
└── README.md
```

## Run the backend

### Requirements

- Python 3.12 or 3.13
- A webcam or external camera
- Windows, macOS, or Linux

### Setup

```bash
git clone https://github.com/NineNights195/smart-traffic-light.git
cd smart-traffic-light/backend
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies and start the prototype:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Press `q` in the OpenCV window to stop it.

### Camera and model settings

Before running, check the configuration at the top of `backend/main.py`:

- `CAM_INDEX` — select the webcam index for the connected camera.
- `MODEL_PATH` — the default model location is `models/yolov8n.pt`. Make sure the weights are available at that path, or update the setting to the checked-in model at `scripts/yolov8n.pt`.
- `CONFIDENCE`, `PERSON_CONFIRM`, and `NO_PERSON_CONFIRM` — tune these values for the camera position and lighting conditions.

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

This starts the development server for the dashboard work. The backend API integration is a planned next step.

## Roadmap

- [ ] Replace the starter frontend with a live traffic-monitoring dashboard.
- [ ] Expose detections and traffic-light state from the Python backend through an API.
- [ ] Connect the dashboard to live camera, detection, and control data.
- [ ] Improve detection accuracy across distance, occlusion, low light, and busy intersections.
- [ ] Add test scenarios and safety rules for predictable light transitions.
- [ ] Deploy the integrated system on Raspberry Pi and connect it to physical light hardware.

## Notes

This is an educational prototype and a simulation. It must not be used to control real public-road traffic without rigorous safety engineering, testing, and approval from the relevant authorities.

## License

See [LICENSE](LICENSE).  
