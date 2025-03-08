import asyncio
import json
import time
import cv2
import numpy as np
import websockets
import dlib
from collections import deque

# Load Dlib's face detector and landmark predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("./frontend/Eye_Tracking/shape_predictor_68_face_landmarks.dat")

# Calibration points (in screen coordinates)
calibration_points = [
    (213, 120), (640, 120), (1067, 120),  # Top row
    (213, 360), (640, 360), (1067, 360),  # Middle row
    (213, 600), (640, 600), (1067, 600)   # Bottom row
]
pupil_positions = []
screen_positions = []

pupil_buffer = deque(maxlen=10)  # Adjust maxlen for more/less smoothing

# Global variables for focus detection on signs
focus_start_time = None
focused_sign = None
FOCUS_THRESHOLD = 1.0  # seconds

# Resolutions (update these based on your setup)
WEBCAM_WIDTH, WEBCAM_HEIGHT = 1280, 720  # Default webcam resolution (used for calibration)
SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080  # Default screen resolution
IMAGE_WIDTH, IMAGE_HEIGHT = 960, 540  # From JSON limit_side_len (assuming 16:9 aspect ratio)

def get_eye_points(landmarks, eye_indices):
    points = [(landmarks.part(i).x, landmarks.part(i).y) for i in eye_indices]
    return np.array(points, dtype=np.int32)

def detect_pupil(gray, eye_points):
    if len(eye_points) == 0:
        print("No eye points detected.")
        return None
    
    x, y, w, h = cv2.boundingRect(eye_points)
    eye_roi = gray[y:y+h, x:x+w]
    
    _, thresh = cv2.threshold(eye_roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        pupil = max(contours, key=cv2.contourArea)
        if len(pupil) >= 5:
            ellipse = cv2.fitEllipse(pupil)
            cx = int(ellipse[0][0]) + x
            cy = int(ellipse[0][1]) + y
            return (cx, cy)
    return None

def get_gaze_direction(pupil, eye_points):
    eye_center = np.mean(eye_points, axis=0).astype(int)
    dx = pupil[0] - eye_center[0]
    dy = pupil[1] - eye_center[1]
    return "Left" if dx < 0 else "Right" if dx > 0 else "Up" if dy < 0 else "Down"

def map_pupil_to_screen(pupil):
    if len(pupil_positions) < 4:
        return (0, 0)
    x = np.interp(pupil[0], [min(p[0] for p in pupil_positions), max(p[0] for p in pupil_positions)], [0, WEBCAM_WIDTH])
    y = np.interp(pupil[1], [min(p[1] for p in pupil_positions), max(p[1] for p in pupil_positions)], [0, WEBCAM_HEIGHT])
    return int(x), int(y)

def calculate_ear(eye_points):
    A = np.linalg.norm(eye_points[1] - eye_points[5])
    B = np.linalg.norm(eye_points[2] - eye_points[4])
    C = np.linalg.norm(eye_points[0] - eye_points[3])
    return (A + B) / (2.0 * C)

def calibrate():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        exit()
        
    print("Starting calibration... Look at each green dot and press 'y' to start calibration for each point.")
    
    for point in calibration_points:
        calib_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.circle(calib_frame, point, 10, (0, 255, 0), -1)
        cv2.imshow('Calibration', calib_frame)
        
        print(f"Look at point {point} and press 'y' to start calibration.")
        while True:
            if cv2.waitKey(1) & 0xFF == ord('y'):
                break
        
        start_time = time.time()
        stable_pupil = None
        detection_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Cannot receive frame.")
                break
            
            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector(gray)
            
            if faces:
                landmarks = predictor(gray, faces[0])
                left_eye_points = get_eye_points(landmarks, range(36, 42))
                pupil = detect_pupil(gray, left_eye_points)
                
                cv2.circle(frame, point, 10, (0, 255, 0), -1)
                
                if pupil:
                    if stable_pupil is None:
                        stable_pupil = pupil
                        detection_count = 1
                    elif abs(pupil[0] - stable_pupil[0]) < 5 and abs(pupil[1] - stable_pupil[1]) < 5:
                        detection_count += 1
                        if detection_count >= 5 and (time.time() - start_time) > 2:
                            start_time = time.time()
                            pupil_positions.append(pupil)
                            screen_positions.append(point)
                            print(f"Recorded pupil position: {pupil} -> {point}")
                            break
                else:
                    print("Pupil not detected")
            
            cv2.imshow('Calibration', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
    cap.release()
    cv2.destroyAllWindows()
    print("Calibration complete! Pupil positions:", pupil_positions)
    print("Screen positions:", screen_positions)
    return len(pupil_positions) > 0

def map_bbox_to_webcam(bbox):
    scale_x = WEBCAM_WIDTH / IMAGE_WIDTH
    scale_y = WEBCAM_HEIGHT / IMAGE_HEIGHT
    x_min = bbox[0] * scale_x
    y_min = bbox[1] * scale_y
    x_max = bbox[2] * scale_x
    y_max = bbox[3] * scale_y
    return [int(x_min), int(y_min), int(x_max), int(y_max)]

def load_ocr_results(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    signs = []
    for i in range(len(data["rec_texts"])):
        bbox_mapped = map_bbox_to_webcam(data["rec_boxes"][i])
        sign = {
            "text": data["rec_texts"][i],
            "x1": bbox_mapped[0],  # x_min
            "y1": bbox_mapped[1],  # y_min
            "x2": bbox_mapped[2],  # x_max
            "y2": bbox_mapped[3],  # y_max
            "score": data["rec_scores"][i],
            "result": {
                "text": data["rec_texts"][i],
                "confidence": data["rec_scores"][i],
                "position": data["dt_polys"][i]
            }
        }
        signs.append(sign)
    return signs

def map_gaze_to_frame(gaze_x, gaze_y, window_x, window_y, window_width, window_height):
    if not (window_x <= gaze_x <= window_x + window_width and 
            window_y <= gaze_y <= window_y + window_height):
        return None, None  # Gaze is outside the window
    
    scale_x = WEBCAM_WIDTH / window_width
    scale_y = WEBCAM_HEIGHT / window_height
    
    x_frame = (gaze_x - window_x) * scale_x
    y_frame = (gaze_y - window_y) * scale_y
    
    return x_frame, y_frame

def map_screen_to_image(screen_x, screen_y, window_width, window_height, image_width, image_height):
    """
    Map screen coordinates to image coordinates based on window size and image resolution.
    """
    scale_x = image_width / window_width
    scale_y = image_height / window_height
    x_image = int(screen_x * scale_x)
    y_image = int(screen_y * scale_y)
    return (x_image, y_image)

def is_gaze_on_sign(gaze_x, gaze_y, window_width, window_height, sign, image_width, image_height):
    x_win, y_win, w_win, h_win = cv2.getWindowImageRect("Test Image")
    gaze_x_frame, gaze_y_frame = map_gaze_to_frame(gaze_x, gaze_y, x_win, y_win, window_width, window_height)
    
    if gaze_x_frame is None or gaze_y_frame is None:
        return False
    
    # Map gaze coordinates to image space
    gaze_x_image, gaze_y_image = map_screen_to_image(gaze_x_frame, gaze_y_frame, window_width, window_height, image_width, image_height)
    
    x1, y1, x2, y2 = sign["x1"], sign["y1"], sign["x2"], sign["y2"]
    return x1 <= gaze_x_image <= x2 and y1 <= gaze_y_image <= y2

def process_ocr_result(sign):
    print("\n=== OCR Result ===")
    print(f"Text: {sign['text']}, Confidence: {sign['score']:.4f}")
    print(f"Bounding Box (in webcam space): [{sign['x1']}, {sign['y1']}, {sign['x2']}, {sign['y2']}]")
    output_dir = "./output"
    import os
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "output.json"), 'w', encoding='utf-8') as f:
        json.dump(sign["result"], f, ensure_ascii=False, indent=4)
    print(f"Saved JSON to {output_dir}/output.json")

async def track_gaze(websocket, path):
    global focus_start_time, focused_sign  # Declare global variables
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        exit()
    
    window_name = "Test Image"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # Load static image
    img_path = "./frontend/Eye_Tracking/test.jpeg"
    image = cv2.imread(img_path)
    if image is None:
        print("Error: Could not load test image.")
        exit()
    
    # Get image dimensions
    image_height, image_width = image.shape[:2]
    print(f"Image dimensions: {image_width}x{image_height}")
    
    # Create a copy of the image to draw on
    display_image = image.copy()
    
    isDetected = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Cannot receive frame.")
            break
        
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray)
        
        # Create a copy of the image to draw on
        display_image = image.copy()
        
        x_win, y_win, w_win, h_win = cv2.getWindowImageRect(window_name)
        # print(f"Window dimensions: {x_win + w_win}x{y_win + h_win}")
        
        # Convert the image to binary format for WebSocket Transmission
        # _, buffer = cv2.imencode('.jpg', display_image)
        # image_bytes = buffer.tobytes()
        
        # await websocket.send(image_bytes)
        
        for face in faces:
            landmarks = predictor(gray, face)
            left_eye_points = get_eye_points(landmarks, range(36, 42))
            right_eye_points = get_eye_points(landmarks, range(42, 48))
            
            left_pupil = detect_pupil(gray, left_eye_points)
            right_pupil = detect_pupil(gray, right_eye_points)
            
            left_ear = calculate_ear(left_eye_points)
            right_ear = calculate_ear(right_eye_points)
            ear_threshold = 0.2
            
            if left_ear > ear_threshold and right_ear > ear_threshold:
                if left_pupil:
                    cv2.circle(frame, left_pupil, 3, (0, 0, 255), -1)
                    direction = get_gaze_direction(left_pupil, left_eye_points)
                    
                    pupil_buffer.append(left_pupil)
                    smoothed_pupil = np.mean(pupil_buffer, axis=0).astype(int)
                    
                    screen_x, screen_y = map_pupil_to_screen(smoothed_pupil)
                    cv2.circle(frame, (screen_x, screen_y), 10, (0, 255, 0), -1)
                    
                    # Load OCR results from JSON
                    signs = load_ocr_results("./frontend/Eye_Tracking/output/test_res.json")
                    
                    # Create a copy of the image to draw on
                    display_image = image.copy()
                    
                    # Draw bounding boxes
                    for sign in signs:
                        cv2.rectangle(display_image, (sign["x1"], sign["y1"]), (sign["x2"], sign["y2"]), (0, 255, 0), 2)
                        cv2.putText(display_image, sign["text"], (sign["x1"], sign["y1"] - 10), cv2.FONT_HERSHEY_COMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # Map screen coordinates to image coordinates and draw gaze circle
                    # cv2.circle(display_image, (screen_x, screen_y), 10, (0, 255, 0), -1)
                    gaze_x_image, gaze_y_image = map_screen_to_image(screen_x, screen_y, x_win + w_win, y_win + h_win, image_width, image_height)
                    # if 0 <= gaze_x_image < image_width and 0 <= gaze_y_image < image_height:
                    cv2.circle(display_image, (gaze_x_image, gaze_y_image), 10, (0, 255, 0), -1)
                    
                    # Focus detection
                    current_sign = None
                    for sign in signs:
                        if is_gaze_on_sign(screen_x, screen_y, w_win, h_win, sign, image_width, image_height):
                            current_sign = sign
                            print(f"Focused on sign: {current_sign['text']}")
                            break
                        
                    print(f"Current sign: {current_sign}")
                    if current_sign:
                        print(f"Focused on sign now: {current_sign['text']}")
                        if focused_sign is None:
                            focused_sign = current_sign
                            focus_start_time = time.time()
                        elif focused_sign == current_sign:
                            if time.time() - focus_start_time >= 0.5:
                                print("Detected focus on sign for 0.5 second.")
                                isDetected = True
                                process_ocr_result(focused_sign)
                                focused_sign = None
                                focus_start_time = None
                        else:
                            focused_sign = current_sign
                            focus_start_time = time.time()
                    else:
                        isDetected = False
                        focused_sign = None
                        focus_start_time = None
                    
                    # Send gaze data to frontend
                    if isDetected:
                        ocr_results = [{"text": s["text"], "x1": s["x1"], "y1": s["y1"], "x2": s["x2"], "y2": s["y2"]} for s in signs]
                    else:
                        ocr_results = []
                    gaze_data = {
                        "x": screen_x,
                        "y": screen_y,
                        "ocr_results": ocr_results
                    }
                    await websocket.send(json.dumps(gaze_data))
                    # print(f"Sending gaze data: {gaze_data}")
                    
                    # Convert the image to binary format for WebSocket Transmission
                    _, buffer = cv2.imencode('.jpg', display_image)
                    image_bytes = buffer.tobytes()
                    
                    await websocket.send(image_bytes)
                    
                if right_pupil:
                    cv2.circle(frame, right_pupil, 3, (0, 0, 255), -1)
                    direction = get_gaze_direction(right_pupil, right_eye_points)
            
            cv2.polylines(frame, [left_eye_points], True, (0, 255, 0), 2)
            cv2.polylines(frame, [right_eye_points], True, (0, 255, 0), 2)
        
        cv2.imshow('Eyes detector', frame)
        cv2.imshow("Test Image", display_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        await asyncio.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()

async def main():
    if calibrate():
        print("Starting WebSocket server...")
        async with websockets.serve(track_gaze, "localhost", 5000):
            print("Server running on ws://localhost:5000")
            await asyncio.Future()
    else:
        print("Calibration Failed. Exiting...")

if __name__ == "__main__":
    asyncio.run(main())