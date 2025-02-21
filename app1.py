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
model = YOLO("yolo11n.pt")
conf_threshold = 0.5  # 可根据需要调整

# 用于存储每个跟踪目标的轨迹历史（仅保留最近 50 个中心点）
track_history = defaultdict(lambda: [])

# 全局卡尔曼滤波器状态字典：每个行人对应一个状态 [x, y, vx, vy] 和协方差矩阵
kf_state = {}

# 卡尔曼滤波器参数（常数）
# 测量矩阵：直接测量位置
H = np.array([[1, 0, 0, 0],
              [0, 1, 0, 0]])
# 测量噪声协方差
R = np.eye(2) * 1.0
# 过程噪声协方差
Q = np.eye(4) * 0.01


def kalman_predict_update(track_id, meas, dt):
    """
    对单个行人进行卡尔曼滤波更新
    :param track_id: 行人ID
    :param meas: 测量值 [x, y]
    :param dt: 两帧时间间隔
    :return: 更新后的状态向量（4x1 ndarray）
    """
    # 状态转移矩阵（常速运动模型）
    F = np.array([[1, 0, dt, 0],
                  [0, 1, 0, dt],
                  [0, 0, 1, 0],
                  [0, 0, 0, 1]])
    # 如果该行人未初始化，则初始化状态：[x, y, 0, 0]，协方差设为较大值
    if track_id not in kf_state:
        state = np.array([[meas[0]], [meas[1]], [0.], [0.]])
        P = np.eye(4) * 100.0
    else:
        state, P = kf_state[track_id]

    # 预测步骤
    state_pred = F @ state
    P_pred = F @ P @ F.T + Q

    # 更新步骤
    z = np.array([[meas[0]], [meas[1]]])
    y_k = z - (H @ state_pred)  # 测量残差
    S = H @ P_pred @ H.T + R
    K = P_pred @ H.T @ np.linalg.inv(S)
    state_new = state_pred + K @ y_k
    P_new = (np.eye(4) - K @ H) @ P_pred

    # 保存更新后的状态
    kf_state[track_id] = (state_new, P_new)
    return state_new


def kalman_predict_future(state, T):
    """
    根据当前状态预测未来T秒的位置（简单常速预测）
    :param state: 当前状态向量 [x, y, vx, vy]
    :param T: 预测时间（秒）
    :return: (x, y)预测位置
    """
    x = state[0, 0]
    y = state[1, 0]
    vx = state[2, 0]
    vy = state[3, 0]
    pred_x = x + vx * T
    pred_y = y + vy * T
    return (int(pred_x), int(pred_y))


def play_webcam():
    video_path = r"C:\Users\26375\Desktop\software\my table2\test.flv"
    vid_cap = cv2.VideoCapture(video_path)

    # 初始化上一帧时间，用于计算dt
    prev_time = time.time()
    fps_history = []

    while vid_cap.isOpened():
        success, frame = vid_cap.read()
        if not success:
            break

        # 在此处先计算dt（单位：秒）
        current_time = time.time()
        dt = current_time - prev_time
        prev_time = current_time

        # 跟踪并检测目标
        results = model.track(frame, persist=True, verbose=False)
        if results and len(results) > 0:
            annotated_frame = results[0].plot(font_size=0.5)
            boxes = results[0].boxes.xywh.cpu()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            classes = results[0].boxes.cls.int().cpu().tolist()
            confidences = results[0].boxes.conf.cpu().tolist()

            for box, track_id, cls, conf_val in zip(boxes, track_ids, classes, confidences):
                # 仅对行人（假设类别 0 为行人）进行处理
                if cls == 0:
                    # box格式为 [x_center, y_center, w, h]，取中心点
                    x, y, _, _ = box
                    center = (float(x), float(y))
                    track_history[track_id].append(center)
                    if len(track_history[track_id]) > 50:
                        track_history[track_id].pop(0)
                    pts = np.array(track_history[track_id], dtype=np.int32).reshape((-1, 1, 2))
                    cv2.polylines(annotated_frame, [pts], isClosed=False, color=(0, 255, 0), thickness=2)

                    # 用卡尔曼滤波器对当前检测进行更新，并预测未来位置
                    # meas: 当前检测的中心坐标
                    state = kalman_predict_update(track_id, center, dt)

                    # 预测未来1秒、2秒、3秒的位置（简单的常速预测）
                    pred_1 = kalman_predict_future(state, 1)
                    pred_2 = kalman_predict_future(state, 2)
                    pred_3 = kalman_predict_future(state, 3)

                    # 在图像上绘制预测点：1秒（红色）、2秒（黄色）、3秒（绿色）
                    cv2.circle(annotated_frame, pred_1, 5, (0, 0, 255), -1)  # 红色
                    cv2.circle(annotated_frame, pred_2, 5, (0, 255, 255), -1)  # 黄色
                    cv2.circle(annotated_frame, pred_3, 5, (0, 255, 0), -1)  # 绿色

                    # 发送 MQTT 消息，将当前置信度发送出去
                    client.publish("Group_99/IMAGE/predict", json.dumps({"confidence": conf_val}), qos=1)
                    print("Confidence:", conf_val)
        else:
            annotated_frame = frame

        # 更新fps_history
        fps = 1 / dt if dt > 0 else 0
        fps_history.append(fps)
        if len(fps_history) > 50:
            fps_history.pop(0)
        fps_text = f'FPS: {fps:.2f}'
        cv2.putText(annotated_frame, fps_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        # 缩放图像
        annotated_frame = cv2.resize(annotated_frame, (960, 540), interpolation=cv2.INTER_LINEAR)

        # 编码JPEG格式
        ret, jpeg = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            continue
        frame_bytes = jpeg.tobytes()

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
