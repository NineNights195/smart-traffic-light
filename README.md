# 🚦 DEPA 2025 : Smart Traffic Light

---

# ⚙️ Setup instruction
### 1. **Install Python 3.13.7**
- Download from [python.org](https://www.python.org/downloads/)
- Make sure to check "Add Python to PATH" during installation
- Check if it installed
  ```bash
  python --version
  ```
  or
  ```bash
  python3 --version
  ```

### 2. **Create Virtual Environment**
- I'd recommended because
   ```bash
   python -m venv venv
   ```

### 4. **Activate Virtual Environment**
   - Windows:
     ```bash
     .\venv\Scripts\activate
     ```

   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

### 5. **Install Dependencies**
  ```bash
  pip install -r requirements.txt
  ```
  - Requrements dependencies
    ```
    opencv-python
    numpy
    torch
    torchvision
    torchaudio
    ultralytics
    ```

### 6. Test some scripts
- Now you can test some scripts in scripts folder
- Example the webcam-test.py
  ```
  python webcam-test.py
  ```
  Now it should work properly
