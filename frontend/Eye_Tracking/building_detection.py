import cv2
from ultralytics import YOLO

model = YOLO("yolo11x.pt") # Load NANO model for speed

def enchance_image(image):
    # Convert to hsv to manipulate brightness
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    # Increase contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    v = clahe.apply(v)
    
    hsv = cv2.merge((h, s, v))
    enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    return cv2.convertScaleAbs(enhanced, alpha=1.5, beta=20)

def detect_building(image):
    image = cv2.imread(image)
    results = model(image, conf=0.1) # Lower confidence threshold to detect more buildings
    
    buildings = []
    for result in results:
        for box in result.boxes:
            class_name = model.names[int(box.cls)]
            if class_name in ["house, skyscraper, tower, building"]:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                buildings.append({"x1:": x1, "y1": y1, "x2": x2, "y2": y2})
                # draw bounding box
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(image, class_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                print(f"Detected {class_name}")
                
    cv2.imshow("Building Detection", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return buildings

if __name__ == "__main__":
    print("Starting")
    print(detect_building("test_img.png"))
    print("Done")