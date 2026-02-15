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

@app.route('/convert', methods=['POST'])
def convert():
    """Process image in memory and return base64 encoded result"""
    try:
        # Validate image upload
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, BMP, WEBP'}), 400
        
        # Get selected style
        style = request.form.get('style', 'modern_art')
        valid_styles = ['pencil_sketch', 'oil_painting', 'modern_art', 'anime']
        if style not in valid_styles:
            style = 'modern_art'  # Default to modern_art
        
        # Read image in memory - NO DISK STORAGE
        image_bytes = file.read()
        
        # Validate image can be decoded
        nparr = np.frombuffer(image_bytes, np.uint8)
        test_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if test_image is None:
            return jsonify({'error': 'Invalid image file'}), 400
        
        # Process image in memory
        result_bytes = process_image_in_memory(image_bytes, style)
        
        if result_bytes is None:
            return jsonify({'error': 'Failed to process image'}), 500
        
        # Return processed image as base64
        import base64
        result_base64 = base64.b64encode(result_bytes).decode('utf-8')
        
        return jsonify({
            'result': f"data:image/png;base64,{result_base64}"
        })
    
    except Exception as e:
        return jsonify({'error': 'An error occurred while processing your image'}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Gunicorn compatibility
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)



