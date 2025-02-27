import time
import cv2
import numpy as np
import dlib
from collections import deque

# Load Dlib's face detector and landmark predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("./frontend/Eye_Tracking/shape_predictor_68_face_landmarks.dat")

# Calibration points (in screen coordinates)
# These are the points where the user is asked to look at during calibration
calibration_points = [
    (213, 120), (640, 120), (1067, 120),  # Top row
    (213, 360), (640, 360), (1067, 360),  # Middle row
    (213, 600), (640, 600), (1067, 600)   # Bottom row
]
pupil_positions = []
screen_positions = []

pupil_buffer = deque(maxlen=10) # Adjust maxlen for more/less smoothing

def get_eye_points(landmarks, eye_indices):
    # Extract the eye coordinates from landmarks
    points = [(landmarks.part(i).x, landmarks.part(i).y) for i in eye_indices]
    return np.array(points, dtype=np.int32)

def detect_pupil(gray, eye_points):
    if len(eye_points) == 0:
        print("No eye points detected.")
        return None
    
    # Get bounding box of eye
    x, y, w, h = cv2.boundingRect(eye_points)
    eye_roi = gray[y:y+h, x:x+w]
    
    # Threshold to isolate dark pupil
    # _, thresh = cv2.threshold(eye_roi, 30, 255, cv2.THRESH_BINARY_INV)
    
    # Adaptive thresholding with Otsu
    _, thresh = cv2.threshold(eye_roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Noise Reduction
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    # Find contours (largest contour is pupil)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        pupil = max(contours, key=cv2.contourArea)
        
        # Need 5+ points for ellipse fitting
        if len(pupil) >= 5:
            ellipse = cv2.fitEllipse(pupil)
            cx = int(ellipse[0][0]) + x
            cy = int(ellipse[0][1]) + y
            return (cx, cy)
            
    return None

# Determine gaze direction: Normalize pupil position to screen coordinates
def get_gaze_direction(pupil, eye_points):
    # Get eye center
    eye_center = np.mean(eye_points, axis=0).astype(int)
    # Normalize pupil position relative to eye center
    dx = pupil[0] - eye_center[0]
    dy = pupil[1] - eye_center[1]
    
    if abs(dx) > abs(dy):
        return "Left" if dx < 0 else "Right"
    else:
        return "Up" if dy < 0 else "Down"

# Simple mapping of eye to screen
def map_pupil_to_screen(pupil):
    if (len(pupil_positions) < 4):
        return (0, 0)
    
    # Simplified linear interpolation
    x = np.interp(pupil[0], [min(p[0] for p in pupil_positions), max(p[0] for p in pupil_positions)], [0, 1280])
    y = np.interp(pupil[1], [min(p[1] for p in pupil_positions), max(p[1] for p in pupil_positions)], [0, 720])
    
    return int(x), int(y)

# def get_head_pose(landmarks):
#     nose = (landmarks.part(30).x, landmarks.part(30).y)
#     chin = (landmarks.part(8).x, landmarks.part(8).y)
#     dx = nose[0] - chin[0]
#     dy = nose[1] - chin[1]
#     angle = np.arctan2(dy, dx) * 180 / np.pi # Convert to degrees
#     return angle

# Calculate Eye Aspect Ratio (EAR)
def calculate_ear(eye_points):
    A = np.linalg.norm(eye_points[1] - eye_points[5])
    B = np.linalg.norm(eye_points[2] - eye_points[4])
    C = np.linalg.norm(eye_points[0] - eye_points[3])
    ear = (A + B) / (2.0 * C)
    return ear

# Calibration with dots
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
            
            # Flip the frame horizontally
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
                    
                    # Check if pupil is stable, if so, record the position
                    # else, update the stable pupil position
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

# Function to track eye gaze
def track_gaze():
    # Initialize camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)  # If supported

    if not cap.isOpened():
        print("Error: Could not open camera.")
        exit()
        
    while True:
        # Capture frame by frame
        # ret is success flag, frame is the image
        ret, frame = cap.read()
        if not ret:
            print("Error: Cannot receive frame.")
            break
        
        # Flip the frame horizontally
        frame = cv2.flip(frame, 1)
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = detector(gray)
        print(f"Number of faces detected: {len(faces)}")
        
        for face in faces:
            try:
                # Get facial landmarks
                landmarks = predictor(gray, face)
                print("Landmarks detected!")
                # print("Total number of landmarks:", landmarks.num_parts)  # Should be 68
                # print("Sample landmark (e.g., nose tip, index 30):", landmarks.part(30).x, landmarks.part(30).y)
                
            except Exception as e:
                print(f"Error in landmark processing: {e}")
                
            # Eye indices: Left(36-41), Right(42-47)
            left_eye_points = get_eye_points(landmarks, range(36, 42))
            right_eye_points = get_eye_points(landmarks, range(42, 48))
            # print("Left eye points:", left_eye_points)
            # print("Right eye points:", right_eye_points)
            
            left_pupil = detect_pupil(gray, left_eye_points)
            right_pupil = detect_pupil(gray, right_eye_points)
            
            # Calculate EAR to ensure eyes are open
            left_ear = calculate_ear(left_eye_points)
            right_ear = calculate_ear(right_eye_points)
            ear_threshold = 0.2  # Adjust threshold as needed
            
            if left_ear > ear_threshold and right_ear > ear_threshold:
                # Draw a dot at the pupil
                if left_pupil:
                    cv2.circle(frame, left_pupil, 3, (0, 0, 255), -1)
                    direction = get_gaze_direction(left_pupil, left_eye_points)
                    
                    # Use mean to stabilize the pupil position
                    pupil_buffer.append(left_pupil)
                    smoothed_pupil = np.mean(pupil_buffer, axis=0).astype(int)
                    
                    screen_x, screen_y = map_pupil_to_screen(smoothed_pupil)
                    print(f"Screen coordinates: ({screen_x}, {screen_y})")
                    cv2.circle(frame, (screen_x, screen_y), 10, (0, 255, 0), -1)
                    
                if right_pupil:
                    cv2.circle(frame, right_pupil, 3, (0, 0, 255), -1)
                    direction = get_gaze_direction(right_pupil, right_eye_points)
            
            # Draw eye outlines (for visualisation)
            cv2.polylines(frame, [left_eye_points], True, (0, 255, 0), 2)
            cv2.polylines(frame, [right_eye_points], True, (0, 255, 0), 2)
        
        # Display the frame (for testing)
        cv2.imshow('Eyes detector', frame)
        
        # Exit on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the capture
    cap.release()
    cv2.destroyAllWindows()
    
# Main function to run the eye tracking
def run_eye_tracking():
    if calibrate():
        track_gaze()
    else:
        print("Calibration failed. Exiting...")
        

if __name__ == "__main__":
    run_eye_tracking()