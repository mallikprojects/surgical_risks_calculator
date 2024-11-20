# Surgical Risk Calculator
> This is a sample project to demonstrate surgical risks analysis and calucluate the risk score. Workflows and the overall approach can be used as foundation to create robustic surgical risk calculator**This should not be used for any production work. Surgical risks parameters are generated using AI and cannot be considered Authentic. Please check with your healthcare provider before undergoing any surgery**

> Main features include
Script to generate list of surgeries and associated risk parameters for each surgery
Flask app that allows to select a specific surgery, upload medical records and caluclate risk score

##prerequsites
`pip install -r requirements.txt`
> openAI apis are used to generate risk parameters and also to calculate risk score. set OPENAI_API_KEY=XXXXX
>Amazon Teseract is used to extract medical report parameters. Uses Boto3. Follow this link to configure AWS credentials. https://docs.aws.amazon.com/textract/latest/dg/setup-awscli-sdk.html
> There are two main components 
###Generate Surgical Parameters (generate_surgical_parameters.py)
>This script uses OpenAI apis to generate lists of surgeries (surgeries.json) and corresponding risks parameters in Parameters directory. This data is pre generated and running this script is optional
`python generate_risk_parameters.py'

###Flask application
`python app.py`
> open the application in web browser and follow the UI to get the surgical risk score

###Limitations
> This is just a demo project and cannot be used for production purpose
> Uploading of JPG/PNG medical reports are supported. MRI/CT Scans, X-Ray are not supported
> PII data is not anonymized
> RIsk score is caluclated bassed on set of instructions to OpenAI. However, a more robustic approach is to to train an AI model ( Simple logistic regression or Deep Nueral Network)
 List of surgeries and associted surgical paramters are AI genrerated and needs to be vetted by qualified healthcare providers