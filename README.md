# How to Run

Follow these step-by-step instructions to run the application:

### Step 1: Open Terminal in Project Folder
```powershell
cd "c:\Users\Abhay\Downloads\Bug report generator (1)\Bug report generator\Bug report generator"
```

---

### Step 2: Activate Virtual Environment
* **PowerShell**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **Command Prompt (cmd.exe)**:
  ```cmd
  .\venv\Scripts\activate.bat
  ```

*(If setting up on a new machine or for the first time, run `python -m venv venv` before activating).*

---

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

### Step 4: Set Up API Key
Ensure a `.env` file exists in the root folder with your Gemini API key:
```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
```

---

### Step 5: Start Server
```bash
python app.py
```

---

### Step 6: Open in Browser
Navigate to **[http://127.0.0.1:5000](http://127.0.0.1:5000)**
