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

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-3.5-flash')

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
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<BugReport {self.id} - {self.title}>'

with app.app_context():
    db.create_all()

def generate_report_from_code(code, language, notes):
    """
    Uses Gemini API to auto-generate a structured report from raw code and error notes.
    """
    prompt = f"""
You are an expert QA Engineer and Senior Developer.
A user has submitted the following {language} code snippet that is causing an issue:

```
{code}
```

Additional notes or error output provided by the user:
"{notes}"

Analyze the code and the notes. Generate a structured bug report.
Return ONLY a valid JSON object with the following keys, and no markdown formatting or extra text outside the JSON:
- "title": A concise summary of the issue.
- "description": A clear breakdown of the problematic behavior or syntax error.
- "steps_to_reproduce": Inferred execution path or trigger (as a numbered list string).
- "expected_result": What the code was logically intended to accomplish.
- "actual_result": The error trace or unexpected output.
- "severity": "Low", "Medium", "High", or "Critical" based on the issue type.
- "priority": "Low", "Medium", "High", or "Critical".
"""

    try:
        response = model.generate_content(prompt)
        text_response = response.text
        # Strip out markdown block if Gemini wraps it in ```json ... ```
        if text_response.strip().startswith('```json'):
            text_response = text_response.strip()[7:-3].strip()
        elif text_response.strip().startswith('```'):
            text_response = text_response.strip()[3:-3].strip()
            
        report_data = json.loads(text_response)
        return report_data
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        raise ValueError(f"Failed to generate report from Gemini API: {e}")

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
                title=generated['title'],
                description=generated['description'],
                steps_to_reproduce=generated['steps_to_reproduce'],
                expected_result=generated['expected_result'],
                actual_result=generated['actual_result'],
                severity=generated['severity'],
                priority=generated['priority'],
                language=language,
                code_snippet=code,
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
