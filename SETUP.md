# Setup Guide: Bug Report Generator

This guide provides step-by-step instructions for installing dependencies and running the Bug Report Generator application.

## Quick Start (3 Steps)

1. **Activate Environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Server**:
   ```bash
   python app.py
   ```
   Open **http://127.0.0.1:5000** in your browser.

---

## Detailed Installation Instructions

### Step 1: Virtual Environment
Ensure you have Python installed. Re-create the virtual environment if switching machines:
```bash
python -m venv venv
```

### Step 2: Activate Virtual Environment
- **PowerShell**: `.\venv\Scripts\Activate.ps1`
- **CMD**: `.\venv\Scripts\activate.bat`

### Step 3: API Key Setup
Create a file named `.env` in the root folder with the following content:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 4: Run Flask Server
```bash
python app.py
```
Visit `http://127.0.0.1:5000` to create and track bug reports.
