# 🚦 DEPA 2025 : Smart Traffic Light

---

## 🛠️ Requirements
- Linux (Ubuntu/Debian recommended) or Windows with Python installed
- Python **3.12 or 3.13**
- Webcam or external camera
- Git

---

## ⚙️ Setup instruction

### 1. **Clone the Repository**
- Clone default branch (main):
```
git clone https://github.com/NineNights195/smart-traffic-light.git
```
- To clone specific branch:
```
git clone -b <branch-name> https://github.com/NineNights195/smart-traffic-light.git
```

### 2. **Create Virtual Environment**
- Go to your repo
  ```
  cd <your repo directory>
  ```
- Create virtual enviroment to prevent using system python
  ```
  python -m venv venv
  ```

### 3. **Activate Virtual Environment**
   - Windows:
     ```bash
     .\venv\Scripts\activate
     ```

   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

### 4. Ensure pip is avaliable
- If pip is missing inside the venv, run:
  ```
  python -m ensurepip --upgrade
  ```

### 5. Upgrade pip, setuptools, and wheel
```
pip install --upgrade pip setuptools wheel
```

### 6. **Install Dependencies**
  ```bash
  pip install -r requirements.txt
  ```
  - Requirements dependencies
    ```
    opencv-python
    numpy
    torch
    torchaudio
    torchvision
    ultralytics
    ultralytics-thop
    pandas
    pillow
    tqdm
    ```

### 7. Test some scripts
- Now you can test some scripts in scripts folder
- Example the webcam-test.py
  ```
  python webcam-test.py
  ```
  Now it should work properly
