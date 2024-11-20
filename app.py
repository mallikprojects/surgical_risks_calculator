# app.py

from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
from werkzeug.utils import secure_filename
import openai
import textract_extractor  # Import the textract_extractor module

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Set your OpenAI API key
openai.api_key = os.environ["OPENAI_API_KEY"]

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route for home page
@app.route('/', methods=['GET', 'POST'])
def home():
    # Load surgeries from JSON file
    with open('surgeries.json', 'r') as f:
        surgeries_data = json.load(f)
    surgeries = []
    for category in surgeries_data['categories']:
        for surgery in category['surgeries']:
            surgeries.append({
                'name': surgery,
                'category': category['category_name']
            })
    if request.method == 'POST':
        selected_surgery = request.form.get('surgery')
        return redirect(url_for('upload_reports', surgery=selected_surgery))
    return render_template('home.html', surgeries=surgeries)

# Route for uploading reports
@app.route('/upload/<surgery>', methods=['GET', 'POST'])
def upload_reports(surgery):
    # Load the parameters for the selected surgery
    surgery_file_base = surgery.replace(' ', '_')
    surgery_parameters_file = os.path.join('parameters', f"{surgery_file_base}_parameters.json")
    if not os.path.exists(surgery_parameters_file):
        flash('Parameters for the selected surgery are not available.')
        return redirect(url_for('home'))
    with open(surgery_parameters_file, 'r') as f:
        parameters_data = json.load(f)
    # Extract the required reports from parameters
    required_reports = set()
    for param in parameters_data:
        reports = param.get("Relevant Medical Reports to Analyze", [])
        required_reports.update(reports)
    required_reports = list(required_reports)
    if request.method == 'POST':
        uploaded_files = {}
        for report in required_reports:
            file = request.files.get(report)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                report_filename = f"{report.replace(' ', '_')}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], report_filename)
                file.save(file_path)
                uploaded_files[report] = file_path
            else:
                flash(f'Invalid file for {report}. Please upload a PNG or JPG image.')
                return redirect(request.url)
        # Save the uploaded_files paths for use in analysis
        # For simplicity, we'll pass the surgery name and store the files in the uploads directory
        return redirect(url_for('analyze', surgery=surgery))
    return render_template('upload.html', surgery=surgery, required_reports=required_reports)

# Route for analysis
@app.route('/analyze/<surgery>', methods=['GET'])
def analyze(surgery):
    # Load the parameters for the selected surgery
    surgery_file_base = surgery.replace(' ', '_')
    surgery_parameters_file = os.path.join('parameters', f"{surgery_file_base}_parameters.json")
    with open(surgery_parameters_file, 'r') as f:
        parameters_data = json.load(f)
    # Extract readings from uploaded images using Amazon Textract
    extracted_data = {}
    uploads_dir = app.config['UPLOAD_FOLDER']
    for filename in os.listdir(uploads_dir):
        file_path = os.path.join(uploads_dir, filename)
        if os.path.isfile(file_path):
            # Use textract_extractor to extract key-value pairs
            with open(file_path, 'rb') as image_file:
                image_bytes = image_file.read()
                kvs = textract_extractor.extract_form_data(image_bytes)
                extracted_data.update(kvs)
    # Perform risk analysis using OpenAI API
    risk_score, analysis_details,risk_level,risk_level_explaination = calculate_risk_score(parameters_data, extracted_data)
    return render_template('results.html', risk_score=risk_score,risk_level=risk_level,risk_level_explaination=risk_level_explaination, analysis_details=analysis_details)

# Function to calculate risk score based on parameters and extracted data using OpenAI API
def calculate_risk_score(parameters, data):
    # Remove any PII/PHI from data
    import pprint
    
    anonymized_data = anonymize_data(data)
    pprint.pprint(anonymized_data)
    # Prepare the prompt for OpenAI API
    prompt = generate_prompt(parameters, anonymized_data)
    # Call OpenAI API to get the risk analysis
    client = openai.OpenAI(api_key=openai.api_key)
    response = client.chat.completions.create(
        model="o1-preview",
        messages=[
            #{"role": "system", "content": "You are an expert in surgical risk analysis."},
            {"role": "user", "content": prompt}
        ],
        #max_tokens=3000,
        #temperature=0.0,
    )
    assistant_reply = response.choices[0].message.content.strip() 
    import pprint
    import re
    pprint.pprint(assistant_reply)

    #json_pattern = r'```json\s*(.*?)\s*```'

    #match = re.search(json_pattern, assistant_reply, re.DOTALL)
    json_pattern = re.compile(r'\{.*\}', re.DOTALL)
    match = json_pattern.search(assistant_reply)

    if match:
        json_content = match.group(0)
        # Now parse the JSON content
        analysis_result = json.loads(json_content)
        risk_score = analysis_result.get('risk_score', 0)
        risk_level = analysis_result.get('risk_level', 2)
        risk_level_explaination = analysis_result.get('risk_level_explaination', "")
        analysis_details = analysis_result.get('analysis_details', [])
        return risk_score, analysis_details,risk_level,risk_level_explaination
    else:
        print("Error: JSON content not found in the assistant's output.")
        

    

def anonymize_data(data):
    # Assuming data is a dictionary of key-value pairs
    # Remove any keys that might contain PII/PHI
    # For example, remove 'Patient Name', 'DOB', 'Address', etc.
    pii_keys = ['Patient Name', 'Date of Birth', 'DOB', 'Address', 'Phone Number', 'Email']
    anonymized_data = {k: v for k, v in data.items() if k not in pii_keys}
    return anonymized_data

def generate_prompt(parameters, data):
    # Convert parameters and data to JSON strings for the prompt
    parameters_str = json.dumps(parameters)
    data_str = json.dumps(data)
    prompt = f"""
You are a medical AI assistant. Based on the following patient data and risk analysis parameters, calculate the total risk score and provide detailed analysis:

Patient Data:
{data_str}

Risk Analysis Parameters:
{parameters_str}

Instructions:
- For each parameter, evaluate the patient's data against the risk analysis rules.
- Calculate the risk multiplier(RiskMultiplier) based on the conditions met.
- use the Multiplicative approach of individual risk multipliers to get the total risk score . Multipler approach involves multiplying individual risk multipliers to get the total score
- Explain on how did you arrive at risk score and provide detailed mathematical analysis for each parameter evaluated and the score for each parmater. 
- explain what parameters from data_str are considered for each paramter valuated
- Provide analysis details for each parameter evaluated.
- overall risk score should be normalized on 0-10 scale. To get maximum combined risk - Calculate the highest possible Combined Risk Multiplier by multiplying all the highest risk muliplers of each paramter from Risk Analysis Parameters data.combined risk multipler is the product of all risk multipler of eac paramter.Risk score can then be caluclated as  ((combined risk multipler -1.0)/(maximum combined risk multipler-1.0))*10
- overall risk level Low, Medium, High, Very High

**Important**: Provide the output in **valid JSON format only**, without any additional text or explanations. The JSON should have the following structure:
{{
  "risk_score": total_risk_score,
  "risk_score_explaination": "explanation_of_risk_score",
  "risk_level": risk_level,
  "risk_level_explaination": "score range for each risk level - low, medium, high,very high",
  "Combined Risk Multiplier": combined_risk_multiplier,
  "Combined Risk Multiplier Explaination": "explanation_of_combined_risk_multiplier",
  "individual risk multipliers": "individual risk multipliers",
  "analysis_details": [
    {{
      "Parameter": "parameter_name",
      "Condition": "condition_evaluated",
      "Risk Increase": "risk_increase_level",
      "Risk Factors": "risk_factors_identified",
      "Risk Multiplier": risk_multiplier_value,
      "Score": score_for_parameter
      "parameters evaluaed": {{ "parameter_name": "value", "parameter_name": "value"
    }},
    ... (more analysis details)
  ]
}}

Do not include any additional text or explanations.
"""
    return prompt

if __name__ == '__main__':
    app.run(debug=True)
