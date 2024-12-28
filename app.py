from flask import Flask, request, render_template, send_file, redirect, url_for
import io
import os
import requests
import base64
import json
import re
from dotenv import load_dotenv

load_dotenv()

GOOGLE_VISION_API_KEY = os.getenv('GOOGLE_VISION_API_KEY')
PROJECT_HOME_PATH=os.getenv('PROJECT_HOME_PATH')

app = Flask(__name__)

# Define the output directory
OUTPUT_DIR =os.path.join(PROJECT_HOME_PATH,'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)  # Ensure the directory exists


# Function to extract text from image
def extract_text_from_image(api_key, image_file):
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    payload = {
        "requests": [
            {
                "image": {
                    "content": base64_image
                },
                "features": [
                    {
                        "type": "TEXT_DETECTION"
                    }
                ]
            }
        ]
    }
    url = f'https://vision.googleapis.com/v1/images:annotate?key={api_key}'
    response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
    response_json = response.json()
    try:
        text_annotations = response_json.get('responses', [])[0].get('textAnnotations', [])
        text = text_annotations[0].get('description', '')
    except (IndexError, KeyError):
        text = ''
    return text


# Function to format extracted text
def format_extracted_text(text):
    formatted_text = re.sub(r'\n+', '\n', text)
    formatted_text = re.sub(r'\\u[0-9a-fA-F]{4}', '', formatted_text)
    formatted_text = re.sub(r'\s{2,}', ' ', formatted_text)
    formatted_text = re.sub(r'(Buyer.*|Bill to.*)', r'\n\1\n', formatted_text)
    formatted_text = re.sub(r'(Consignee.*|Ship to.*)', r'\n\1\n', formatted_text)
    formatted_text = re.sub(r'(Invoice No.*|Invoice Date.*)', r'\n\1\n', formatted_text)
    formatted_text = re.sub(r'(Total.*|Amount.*|GSTIN.*)', r'\n\1\n', formatted_text)
    formatted_text = re.sub(r'(Description of Goods.*|Contact.*|Transport.*)', r'\n\1\n', formatted_text)
    formatted_text = formatted_text.strip()
    return formatted_text


# Route for home page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['image']
        if file:
            text = extract_text_from_image(GOOGLE_VISION_API_KEY, file)
            formatted_text = format_extracted_text(text)
            
            # Save the text to a file
            file_path = os.path.join(OUTPUT_DIR, 'extracted_text.txt')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
            
            return render_template('index.html', text=formatted_text, download_available=True)
    return render_template('index.html', download_available=False)


# Route for downloading file
@app.route('/download')
def download_file():
    file_path = os.path.join(OUTPUT_DIR, 'extracted_text.txt')
    if os.path.exists(file_path):
        return send_file(
            file_path,
            as_attachment=True,
            download_name='extracted_text.txt',
            mimetype='text/plain'
        )
    return "File not found", 404


if __name__ == '__main__':
    app.run(debug=True)
