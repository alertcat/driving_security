# Send gaze data to frontend
                    if isDetected:
                        ocr_results = [{"text": s["text"], "x1": s["x1"], "y1": s["y1"], "x2": s["x2"], "y2": s["y2"]} for s in signs]
                    else:
                        ocr_results = ""
                    gaze_data = {"x": screen_x, "y": screen_y, "ocr_results": ocr_results}