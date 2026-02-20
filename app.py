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
    return cv2.GaussianBlur(image, (15, 15), 0)

def convert_to_modern_art(image):
    """Convert image to modern art style"""
    return cv2.applyColorMap(image, cv2.COLORMAP_JET)

def convert_to_anime(image):
    """Convert image to anime style"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    return cv2.bitwise_and(image, edges)

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
    
        


        if file.filename == '':
            return "No image selected", 400

        if not allowed_file(file.filename):
            return "Invalid file type", 400

        # Save uploaded file
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(filepath)

        # Read image
        image = cv2.imread(filepath)
        

        if image is None:
            return jsonify({"error": "Failed to read image"}), 400

        # Resize to reduce memory usage
        height, width = image.shape[:2]

        if width > 1000 or height > 1000:
            image = cv2.resize(image, (800, 800))
                
                # Resize to reduce memory usage
      

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
        if image is None:
            return jsonify({"error": "Invalid image file"}), 400

        # Resize large images immediately (IMPORTANT FOR RENDER FREE PLAN)
        h, w = image.shape[:2]
        if h > 1200 or w > 1200:
            scale = 1200 / max(h, w)
            new_size = (int(w * scale), int(h * scale))
            image = cv2.resize(image, new_size)

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
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


