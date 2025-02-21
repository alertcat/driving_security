from flask import Flask, Response, render_template
import cv2
from ultralytics import YOLO
import paho.mqtt.client as mqtt
import json
import time
from collections import defaultdict
import numpy as np

app = Flask(__name__)

# MQTT 全局变量与设置
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected to broker.")
        client.subscribe("Group_99/IMAGE/predict", qos=1)
    else:
        print("Connection failed with code: %d." % rc)

def setup(hostname):
    client.on_connect = on_connect
    client.connect(hostname)
    client.loop_start()
    return client

# 加载 YOLO11 模型（请确保模型文件路径正确）
# 若你原来使用 best.pt，请将其替换为 yolo11 相关的模型文件，如 "yolo11n.pt"
model = YOLO("yolo11n.pt")
conf_threshold = 0.5  # 可根据需要调整

# 用于存储每个跟踪目标的轨迹历史（仅保留最近 30 个中心点）
track_history = defaultdict(lambda: [])

def play_webcam():
    #source_webcam = 0  # 0 表示默认摄像头；如需使用视频文件，可替换为文件路径
    #vid_cap = cv2.VideoCapture(source_webcam)
    video_path = r"C:\Users\26375\Desktop\software\my table2\test.flv"
    vid_cap = cv2.VideoCapture(video_path)
    prev_time = time.time()

    while vid_cap.isOpened():
        success, frame = vid_cap.read()
        if not success:
            break

        # 直接使用原始彩色图像进行跟踪
        # 若需要其他预处理，请自行添加
        #results = model.track(frame, persist=True)
        results = model.track(frame, persist=True, verbose=False)
        if results and len(results) > 0:
            # 获取绘制了检测框、跟踪 ID 等信息的图像
            #annotated_frame = results[0].plot()
            annotated_frame = results[0].plot(font_size=0.5)
            # 从结果中提取检测框（xywh）、跟踪 ID、类别以及置信度
            boxes = results[0].boxes.xywh.cpu()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            classes = results[0].boxes.cls.int().cpu().tolist()
            confidences = results[0].boxes.conf.cpu().tolist()

            # 遍历每个检测结果
            for box, track_id, cls, conf_val in zip(boxes, track_ids, classes, confidences):
                # 仅对行人（假设类别 0 为行人）进行轨迹绘制
                if cls == 0:
                    # box 为 [x_center, y_center, w, h]，取中心点 (x, y)
                    x, y, _, _ = box
                    track_history[track_id].append((float(x), float(y)))
                    # 保持每个轨迹最多记录 30 个点
                    if len(track_history[track_id]) > 50:
                        track_history[track_id].pop(0)
                    pts = np.array(track_history[track_id], dtype=np.int32).reshape((-1, 1, 2))
                    cv2.polylines(annotated_frame, [pts], isClosed=False, color=(0, 255, 0), thickness=2)

                    # 发送 MQTT 消息，将当前置信度发送出去
                    client.publish("Group_99/IMAGE/predict", json.dumps({"confidence": conf_val}), qos=1)
                    print("Confidence:", conf_val)
        else:
            annotated_frame = frame

        # 计算并在图像上绘制 FPS
        current_time = time.time()
        fps = 1 / (current_time - prev_time)
        prev_time = current_time
        fps_text = f'FPS: {fps:.2f}'
        cv2.putText(annotated_frame, fps_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        # 将图像缩放为 960x540，保持原有网页显示样式
        annotated_frame = cv2.resize(annotated_frame, (960, 540), interpolation=cv2.INTER_LINEAR)

        # 编码图像为 JPEG 格式
        ret, jpeg = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            continue
        frame_bytes = jpeg.tobytes()

        # 以 MJPEG 流形式输出每一帧
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

    vid_cap.release()


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/video_feed')
def video_feed():
    return Response(play_webcam(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    setup("127.0.0.1")
    app.run(host='0.0.0.0', port=8000, debug=True)
