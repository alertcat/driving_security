import cv2
import pytesseract
import numpy as np

# Path to tesseract exe file (must download from github: https://github.com/UB-Mannheim/tesseract/wiki)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
config = r'--oem 3 --psm 6'

# Preprocess image to improve OCR accuracy
def preprocess_image(image):
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    # Apply thresholding to make text stand out
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return thresh
images = None
# Detect and extract text from image
def detect_signage(image_path):
    image = cv2.imread(image_path)
    if image is None:
        print("Image not found")
        return []
    
    processed = preprocess_image(image)
    
    # Run tessearct OCR on the image
    text = pytesseract.image_to_string(processed, config=config)
    
    # Split text into lines and clean up
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    # Find potential names of buildings/restaurants
    names = []
    for line in lines:
        if any(word.isupper() or word.istitle() for word in line.split()):
            names.append(line)
            
    print("Detected names:", names)
    
    # Draw bounding box around text
    h, w = processed.shape
    boxes = pytesseract.image_to_boxes(processed, config=config)
    for b in boxes.splitlines():
        b = b.split()
        x1, y1, x2, y2 = int(b[1]), h - int(b[4]), int(b[3]), h - int(b[2])
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
    cv2.imshow("Sign Detection", image)
    # return names
    
if __name__ == "__main__":
    image_path = "./frontend/Eye_Tracking/assets/alamaan.jpg"
    detect_signage(image_path)
    names = detect_signage(image_path)
    # print("Detected names:", names)