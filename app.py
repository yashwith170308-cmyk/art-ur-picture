from flask import Flask, render_template, request, jsonify, send_file
import cv2
import numpy as np
import os
import io
import uuid
import time
import logging
logging.basicConfig(level=logging.INFO)

def cleanup_old_files(folder, max_age_seconds=3600):
    now = time.time()
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                os.remove(file_path)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB limit


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
    blur = cv2.GaussianBlur(gray, (21, 21), 0)
    sketch = cv2.divide(gray, blur, scale=256)
    return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)


def convert_to_oil_painting(image):
    """Convert image to oil painting style"""
   
    return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)


def convert_to_modern_art(image):
    try:
        # Slight contrast boost
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = cv2.equalizeHist(l)
        lab = cv2.merge((l, a, b))
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # LIGHT bilateral filter (less blur)
        smooth = cv2.bilateralFilter(enhanced, 5, 40, 40)

        # Sharpening kernel
        kernel = np.array([
            [0, -1, 0],
            [-1, 5,-1],
            [0, -1, 0]
        ])
        sharpened = cv2.filter2D(smooth, -1, kernel)

        # Stronger edges
        gray = cv2.cvtColor(sharpened, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 180)
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        modern = cv2.addWeighted(sharpened, 0.9, edges, 0.4, 0)

        return modern

    except Exception as e:
        print("Modern art error:", e)
        return image

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

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route('/convert', methods=['POST'])
def convert():
        cleanup_old_files(app.config["UPLOAD_FOLDER"])
        logging.info("Image processing started")
        

           
        if 'image' not in request.files:
            return "No image uploaded", 400

        file = request.files['image']
        print("Received file:", file.filename)
    
        


        if file.filename == '':
            return "No image selected", 400

        if not allowed_file(file.filename):
            return "Invalid file type", 400

        # Save uploaded file
        unique_name = f"{int(time.time())}_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        file.save(filepath)
        print("Saved at:", filepath)

        # Read image
        image = cv2.imread(filepath)
        

        if image is None:
            return jsonify({"error": "Failed to read image"}), 400

            # Smart high-quality resize
        max_size = 1100

        height, width = image.shape[:2]

        if max(height, width) > max_size:
            scale = max_size / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)

            image = cv2.resize(
                image,
                (new_width, new_height),
                interpolation=cv2.INTER_LANCZOS4
            )

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


