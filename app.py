import os
import datetime
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bugs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configure Gemini API with REST transport to avoid gRPC connection hanging
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"), transport='rest')

CANDIDATE_MODELS = [
    'gemini-flash-lite-latest',
    'gemini-3.1-flash-lite',
    'gemini-3.5-flash-lite',
    'gemini-flash-latest',
    'gemini-3.8-flash',
    'gemini-3.6-flash'
]

class BugReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    steps_to_reproduce = db.Column(db.Text, nullable=False)
    expected_result = db.Column(db.Text, nullable=False)
    actual_result = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='Open')
    language = db.Column(db.String(50), nullable=True)
    code_snippet = db.Column(db.Text, nullable=True)
    fixed_code_snippet = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<BugReport {self.id} - {self.title}>'

with app.app_context():
    db.create_all()
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('bug_report')]
        if 'fixed_code_snippet' not in columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE bug_report ADD COLUMN fixed_code_snippet TEXT;"))
                conn.commit()
    except Exception as e:
        print(f"Migration note: {e}")

def to_str(val):
    if isinstance(val, list):
        return "\n".join(str(x) for x in val)
    return str(val) if val is not None else ""

def generate_report_from_code(code, language, notes):
    """
    Uses Gemini API to auto-generate a structured report and fixed code from raw code and error notes.
    Strictly uses Gemini API. Raises an exception if API calls fail.
    """
    prompt = f"""
You are an expert QA Engineer and Senior Developer.
A user has submitted the following {language} code snippet:

```
{code}
```

Additional notes or error output provided by the user:
"{notes}"

Analyze the code and the notes.
1. If the code CONTAINS BUGS or syntax/logic errors:
   - Provide a detailed report.
   - Set "severity" and "priority" to "Low", "Medium", "High", or "Critical".
   - Provide the corrected working code snippet in "fixed_code".

2. If the code IS CLEAN, CORRECT, and HAS NO BUGS or errors:
   - Clearly state that the code is clean and functional in "title" and "description".
   - Set "steps_to_reproduce" to "N/A - Code is clean and functional."
   - Set "actual_result" to "Code executed successfully with no errors."
   - Set "severity" to "None"
   - Set "priority" to "None"
   - Set "fixed_code" to "" (empty string, as no fix is required).

Return ONLY a valid JSON object with the following keys, and no markdown formatting or extra text outside the JSON:
- "title": A concise summary (e.g. "No Bugs Detected: Code is Functional" if clean).
- "description": Clear explanation of the code or description of the bug.
- "steps_to_reproduce": Execution path/trigger or "N/A - Code is clean".
- "expected_result": What the code accomplishes.
- "actual_result": The error output or "Code executed as expected".
- "severity": "None", "Low", "Medium", "High", or "Critical".
- "priority": "None", "Low", "Medium", "High", or "Critical".
- "fixed_code": Corrected code snippet if buggy, or "" if clean.
"""

    last_error = None
    for model_name in CANDIDATE_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            # Set a 15-second timeout so requests never hang or buffer indefinitely
            response = model.generate_content(prompt, request_options={'timeout': 15})
            text_response = response.text.strip()
            if text_response.startswith('```json'):
                text_response = text_response[7:-3].strip()
            elif text_response.startswith('```'):
                text_response = text_response[3:-3].strip()
                
            report_data = json.loads(text_response)
            return report_data
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            last_error = e

    # Strictly fail and raise exception if Gemini API fails
    raise ValueError(f"Gemini API Error: {last_error}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        code = request.form.get('code')
        language = request.form.get('language')
        notes = request.form.get('notes')
        
        try:
            # Auto-generate the report structure using Gemini API
            generated = generate_report_from_code(code, language, notes)
            
            report = BugReport(
                title=to_str(generated.get('title', 'Bug Report')),
                description=to_str(generated.get('description', '')),
                steps_to_reproduce=to_str(generated.get('steps_to_reproduce', '')),
                expected_result=to_str(generated.get('expected_result', '')),
                actual_result=to_str(generated.get('actual_result', '')),
                severity=to_str(generated.get('severity', 'Medium')),
                priority=to_str(generated.get('priority', 'Medium')),
                language=language,
                code_snippet=code,
                fixed_code_snippet=to_str(generated.get('fixed_code', '')),
                notes=notes
            )
            
            db.session.add(report)
            db.session.commit()
            
            flash('Bug report successfully generated!', 'success')
            return redirect(url_for('report_detail', report_id=report.id))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('index'))
        
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    reports = BugReport.query.order_by(BugReport.created_at.desc()).all()
    return render_template('dashboard.html', reports=reports)

@app.route('/report/<int:report_id>', methods=['GET', 'POST'])
def report_detail(report_id):
    report = BugReport.query.get_or_404(report_id)
    
    if request.method == 'POST':
        new_status = request.form.get('status')
        if new_status in ['Open', 'In Progress', 'Resolved', 'Closed']:
            report.status = new_status
            db.session.commit()
            flash('Status updated successfully.', 'success')
            return redirect(url_for('report_detail', report_id=report.id))
            
    return render_template('report.html', report=report)

if __name__ == '__main__':
    app.run(debug=True)
