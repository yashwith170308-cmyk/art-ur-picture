from flask import Flask, render_template, request, jsonify, send_file
import cv2
import numpy as np
import io

app = Flask(__name__)


app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Security: Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    """Check if file has allowed extension"""
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_to_pencil_sketch(image):
    """Convert image to pencil sketch style"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    inverted = 255 - gray
    blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
    inverted_blur = 255 - blurred
    sketch = cv2.divide(gray, inverted_blur, scale=256.0)
    return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

def convert_to_oil_painting(image):
    """Convert image to oil painting style"""
    result = cv2.bilateralFilter(image, 9, 250, 250)
    result = cv2.convertScaleAbs(result, alpha=1.2, beta=10)
    result = cv2.medianBlur(result, 5)
    return result

def convert_to_modern_art(image):
    """Convert image to modern art style"""
    result = cv2.edgePreservingFilter(image, flags=cv2.RECURS_FILTER, sigma_s=60, sigma_r=0.4)
    result = cv2.convertScaleAbs(result, alpha=1.3, beta=5)
    result = cv2.stylization(result, sigma_s=60, sigma_r=0.6)
    return result

def convert_to_anime(image):
    """Convert image to anime style"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                   cv2.THRESH_BINARY, 9, 5)
    result = cv2.bilateralFilter(image, 9, 250, 250)
    result = result.astype(np.float32)
    result = np.floor(result / 32) * 32
    result = np.clip(result, 0, 255).astype(np.uint8)
    edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    result = cv2.bitwise_and(result, result, mask=cv2.bitwise_not(edges))
    result = cv2.bitwise_or(result, edges_colored)
    return result

def process_image_in_memory(image_bytes, style):
    """Process image entirely in memory - no disk storage"""
    # Decode image from bytes
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        return None
    
    # Apply the selected style
    if style == 'pencil_sketch':
        result = convert_to_pencil_sketch(image)
    elif style == 'oil_painting':
        result = convert_to_oil_painting(image)
    elif style == 'modern_art':
        result = convert_to_modern_art(image)
    elif style == 'anime':
        result = convert_to_anime(image)
    else:
        result = image
    
    # Encode result to bytes
    _, buffer = cv2.imencode('.png', result)
    return buffer.tobytes()

@app.route('/')
def index():
    return render_template('index.html')


import os
from flask import send_file

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route('/convert', methods=['POST'])
def convert():

        if 'image' not in request.files:
            return "No image uploaded", 400

        file = request.files['image']
        # Limit file size to 2MB
        if request.content_length and request.content_length > 2 * 1024 * 1024:
            return "File too large (Max 2MB)", 400


        if file.filename == '':
            return "No image selected", 400

        if not allowed_file(file.filename):
            return "Invalid file type", 400

        # Save uploaded file
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(filepath)

        # Read image
        image = cv2.imread(filepath)
                # Resize to reduce memory usage
        height, width = image.shape[:2]

        if width > 1000 or height > 1000:
            image = cv2.resize(image, (800, 800))


        style = request.form.get('style', 'modern_art')

        if style == 'pencil_sketch':
            result = convert_to_pencil_sketch(image)
        elif style == 'oil_painting':
            result = convert_to_oil_painting(image)
        elif style == 'modern_art':
            result = convert_to_modern_art(image)
        elif style == 'anime':
            result = convert_to_anime(image)
        else:
            result = image

# Save result image
        result_filename = "result_" + file.filename
        result_path = os.path.join(app.config["UPLOAD_FOLDER"], result_filename)
        cv2.imwrite(result_path, result)
        del image
        del result



        return jsonify({
            "original": "/" + filepath,
            "result": "/" + result_path
        })








@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Gunicorn compatibility
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)



