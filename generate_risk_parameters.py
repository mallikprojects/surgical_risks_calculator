# Import necessary libraries
import openai
import json
import openpyxl
from openpyxl import Workbook
import os
import re
import pprint

# Set your OpenAI API key
openai.api_key = os.environ["OPENAI_API_KEY"]

# Configurable directories
OUTPUT_DIR = 'output'       # Directory to store Excel files
PARAMETERS_DIR = 'parameters'  # Directory to store JSON parameter files

# Function to generate surgeries.json using OpenAI
def generate_surgeries_json():
    prompt = """
    As an expert surgeon and medical data analyst, provide a JSON list of surgical procedures grouped by their surgical categories. Each category should include a list of surgeries under it. Present the output in raw JSON format only, without any additional text or explanations.

    The JSON structure should be as follows:

    {
        "categories": [
            {
                "category_name": "Category Name",
                "surgeries": [
                    "Surgery Name 1",
                    "Surgery Name 2",
                    ...
                ]
            },
            ...
        ]
    }
    """

    # Call OpenAI API to generate surgeries.json
    client = openai.OpenAI(api_key=openai.api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert surgeon and medical data analyst."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=3000,
        temperature=0.0  # Set temperature to 0 for deterministic output
    )

    assistant_reply = response.choices[0].message.content.strip()
    surgeries_data = json.loads(assistant_reply)
    return surgeries_data
    #json_pattern = re.compile(r'\{.*?\}', re.DOTALL)
    #match = json_pattern.search(assistant_reply)

    #json_pattern = r'```json\s*(.*?)\s*```'
    #assistant_reply = response.choices[0].message.content
    #json_pattern = r'```json\s*(.*?)\s*```'
    #json_pattern = re.compile(r'\{.*?\}', re.DOTALL)
    #match = json_pattern.search(assistant_reply)
    #match = re.search(json_pattern, assistant_reply, re.DOTALL)
    '''
    if match:
                json_content = match.group(0)
                pprint.pprint(json_content)
                
                surgeries_data = json.loads(json_content)
                return surgeries_data
                
    else:
                print(f"JSON decoding failed for surgeries list: {assistant_reply}")
                return None
    '''

# Function to generate risk analysis parameters for a surgery
def generate_risk_parameters(surgery_name):
    prompt = f"""
    As an expert surgeon specializing in {surgery_name}, provide a comprehensive list of patient parameters that should be collected for preoperative risk analysis. Consider patients with comorbidities such as diabetes, cardiology issues, etc. Take a holistic approach.

    For each parameter, include:

    - Parameter Name
    - Description
    - Relevant Medical Reports to Analyze
    - Risk Analysis Rules with quantitative thresholds (if applicable)

    For each of the above parameters be very specific, what are the reports to be analyzed. Also elaborate rules with more quantitative parameters so that this JSON can be fed to an AI system for processing. Present the output in raw JSON format only, without any additional text or explanations.
    Sample parameter
    {{
      "Name": "DiabetesMellitus",
      "Description": "Presence of Type 1 or Type 2 diabetes.",
      "ReportsToAnalyze": ["Fasting blood glucose levels", "HbA1c test results", "Patient's medical history"],
      "RiskAnalysisRules": [
        {{
          "Condition": "HbA1c > 7%",
          "RiskIncrease": "Significant",
          "RiskFactors": ["Higher risk of infection", "Delayed wound healing"],
          "RiskMultiplier": 1.3
        }},
        {{
          "Condition": "HbA1c <= 7%",
          "RiskIncrease": "Baseline",
          "RiskFactors": [],
          "RiskMultiplier": 1.0
        }}
      ]
    }}
"""
    client = openai.OpenAI(api_key=openai.api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert surgeon and medical data analyst."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=3000,
        temperature=0.0  # Set temperature to 0 for deterministic output
    )
    # Extract the assistant's reply
    assistant_reply = response.choices[0].message.content
    json_pattern = r'```json\s*(.*?)\s*```'
    

    match = re.search(json_pattern, assistant_reply, re.DOTALL)

    if match:
                json_content = match.group(1)
                # Now parse the JSON content
                parameters_data = json.loads(json_content)
                return parameters_data
    else:
                print(f"Failed to parse risk parameters for {surgery_name}")
                return None

          

# Function to process surgeries
def process_surgeries(surgeries_data, output_dir, parameters_dir, max_surgeries=None):
    # Keep track of the number of surgeries processed
    surgeries_processed = 0

    for category in surgeries_data['categories']:
        category_name = category['category_name']
        surgeries_list = category['surgeries']

        # Create category subdirectory in output_dir for Excel files
        category_output_dir = os.path.join(output_dir, category_name.replace(' ', '_'))
        os.makedirs(category_output_dir, exist_ok=True)

        # Create category subdirectory in parameters_dir for JSON files
        #category_parameters_dir = os.path.join(parameters_dir, category_name.replace(' ', '_'))
        #os.makedirs(category_parameters_dir, exist_ok=True)
        category_parameters_dir = parameters_dir

        for surgery in surgeries_list:
            if max_surgeries is not None and surgeries_processed >= max_surgeries:
                break

            print(f"Processing surgery: {surgery} in category: {category_name}")

            # Generate risk parameters
            parameters_data = generate_risk_parameters(surgery)
            if parameters_data is None:
                continue  # Skip this surgery if we couldn't parse the JSON

            # Define file names
            surgery_file_base = surgery.replace(' ', '_')
            json_file_path = os.path.join(category_parameters_dir, f"{surgery_file_base}_parameters.json")
            excel_file_path = os.path.join(category_output_dir, f"{surgery_file_base}_parameters.xlsx")

            # Save the JSON output to a file
            with open(json_file_path, 'w') as json_file:
                json.dump(parameters_data, json_file, indent=2)

            # Create an Excel workbook and worksheet
            wb = Workbook()
            ws = wb.active
            ws.title = f"{surgery_file_base}_Parameters"

            # Define the headers
            headers = ["Name", "Description", "ReportsToAnalyze", "RiskAnalysisRules"]

            # Write the headers to the worksheet
            ws.append(headers)

            # Check if parameters_data is a list or dict
            if isinstance(parameters_data, dict):
                parameters_list = [parameters_data]  # Wrap in a list
            elif isinstance(parameters_data, list):
                parameters_list = parameters_data
            else:
                print(f"Unexpected data format for surgery {surgery}")
                continue  # Skip this surgery

            # Populate the worksheet with data
            for param in parameters_list:
                ws.append([
                    param.get("Name", ""),
                    param.get("Description", ""),
                    ", ".join(param.get("ReportsToAnalyze", [])),
                    json.dumps(param.get("RiskAnalysisRules", []))
                ])

            # Save the Excel file
            wb.save(excel_file_path)

            print(f"Data for surgery '{surgery}' has been saved to '{json_file_path}' and '{excel_file_path}'.")

            surgeries_processed += 1

            if max_surgeries is not None and surgeries_processed >= max_surgeries:
                break  # Exit the loop after processing max_surgeries

# Main function
if __name__ == "__main__":
    # Create the output and parameters directories if they don't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PARAMETERS_DIR, exist_ok=True)

    # Generate surgeries.json using OpenAI
    surgeries_data = generate_surgeries_json()
    if surgeries_data is None:
        print("Failed to generate surgeries.json. Exiting.")
        exit(1)

    # Save surgeries.json to file
    surgeries_json_file = 'surgeries.json'
    with open(surgeries_json_file, 'w') as f:
        json.dump(surgeries_data, f, indent=2)

    # Process the surgeries
    process_surgeries(surgeries_data, OUTPUT_DIR, PARAMETERS_DIR, max_surgeries=None)
