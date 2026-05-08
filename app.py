import os
import fitz  # PyMuPDF
from google import genai  # New import
from flask import Flask, request, render_template
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit
os.makedirs('uploads', exist_ok=True)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-3.1-flash-lite"

def extract_text_from_pdf(filepath):
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()

def analyze_cv(cv_text, job_description):
    prompt = f"""
You are an expert career coach and technical recruiter.

Analyze this CV against the job description and return your response in EXACTLY this format:

MATCH_SCORE: [number 0-100]

STRENGTHS:
- [strength 1]
- [strength 2]
- [strength 3]

GAPS:
- [gap 1]
- [gap 2]
- [gap 3]

SUGGESTIONS:
- [specific improvement 1]
- [specific improvement 2]
- [specific improvement 3]

SUMMARY:
[2-3 sentence overall assessment]

---
CV:
{cv_text}

---
JOB DESCRIPTION:
{job_description}
"""
    response = client.models.generate_content(
    model=MODEL_ID,
    contents=prompt
    )
    return response.text

def parse_analysis(raw_text):
    result = {
        "score": 0,
        "strengths": [],
        "gaps": [],
        "suggestions": [],
        "summary": ""
    }
    lines = raw_text.split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if line.startswith("MATCH_SCORE:"):
            try:
                result["score"] = int(''.join(filter(str.isdigit, line.split(":")[1])))
            except:
                result["score"] = 0
        elif line == "STRENGTHS:":
            current_section = "strengths"
        elif line == "GAPS:":
            current_section = "gaps"
        elif line == "SUGGESTIONS:":
            current_section = "suggestions"
        elif line == "SUMMARY:":
            current_section = "summary"
        elif line.startswith("- ") and current_section in ["strengths", "gaps", "suggestions"]:
            result[current_section].append(line[2:])
        elif current_section == "summary" and line and not line.startswith("---"):
            result["summary"] += line + " "

    return result

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    if 'cv_file' not in request.files:
        return "No file uploaded", 400

    file = request.files['cv_file']
    job_desc = request.form.get('job_description', '').strip()

    if file.filename == '' or not job_desc:
        return "Please upload a CV and enter a job description", 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    cv_text = extract_text_from_pdf(filepath)
    os.remove(filepath)  # clean up after extraction

    raw_analysis = analyze_cv(cv_text, job_desc)
    result = parse_analysis(raw_analysis)

    return render_template("result.html", result=result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)