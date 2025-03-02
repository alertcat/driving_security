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
conf_threshold = 0.4  # 可根据需要调整

# 用于存储每个跟踪目标的轨迹历史（仅保留最近 50 个中心点）
track_history = defaultdict(lambda: [])

# 用于存储最近的帧间隔，用于平滑 dt
dt_history = []


# ------------------- 基于SVD的轨迹预测（EigenTrajectory） ------------------- #
def eigen_trajectory_prediction(trajectory, future_seconds, dt):
    """
    使用SVD对轨迹进行低秩近似，并外推预测未来位置
    :param trajectory: list，形如[(x,y), ...]，轨迹历史
    :param future_seconds: 预测未来的秒数
    :param dt: 平均帧间隔（秒）
    :return: (x, y) 预测位置
    """
    X = np.array(trajectory)  # shape (T,2)
    T_frames = X.shape[0]
    if T_frames < 2:
        return (int(X[-1, 0]), int(X[-1, 1]))
    # 1) 中心化
    mean_X = np.mean(X, axis=0)
    X_centered = X - mean_X
    # 2) SVD 分解
    U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)
    # 3) 选取第一主成分方向
    principal_direction = Vt[0]  # shape (2,)
    # 4) 计算每帧在主方向上的投影系数
    a = X_centered @ principal_direction  # shape (T_frames,)
    # 5) 构造时间向量
    t_vec = np.arange(T_frames) * dt
    # 6) 对投影系数做线性拟合
    A = np.vstack([t_vec, np.ones(len(t_vec))]).T  # (T_frames, 2)
    alpha, beta = np.linalg.lstsq(A, a, rcond=None)[0]
    # 7) 外推到 future_seconds
    t_future = t_vec[-1] + future_seconds
    a_future = alpha * t_future + beta
    # 8) 反投影回原坐标
    pred = mean_X + a_future * principal_direction
    return (int(pred[0]), int(pred[1]))


# ------------------- 基于末 20 帧的平滑速度估计 ------------------- #
def smooth_velocity_prediction(trajectory, future_seconds, dt, window_size=20):
    """
    对末 window_size 帧 (x,y) 做一阶线性回归，得到平滑的速度与初始位置，再外推 future_seconds。
    :param trajectory: list，形如[(x,y), ...]，轨迹历史
    :param future_seconds: 预测未来秒数
    :param dt: 平均帧间隔
    :param window_size: 用多少帧来回归速度，默认 20
    :return: (x, y) 预测位置
    """
    T = len(trajectory)
    if T < 2:
        return trajectory[-1]

    # 如果轨迹不足 window_size 帧，则使用全部帧
    w = min(window_size, T)
    # 取最后 w 帧
    sub_traj = np.array(trajectory[-w:])  # shape (w, 2)
    # 时间向量
    t_vec = np.arange(w) * dt

    # 对 x(t) 做线性回归
    A = np.vstack([t_vec, np.ones(len(t_vec))]).T  # shape (w, 2)
    x_data = sub_traj[:, 0]
    alpha_x, beta_x = np.linalg.lstsq(A, x_data, rcond=None)[0]

    # 对 y(t) 做线性回归
    y_data = sub_traj[:, 1]
    alpha_y, beta_y = np.linalg.lstsq(A, y_data, rcond=None)[0]

    # 回归得到速度 alpha_x, alpha_y，初始位置 beta_x, beta_y
    # 预测时刻 = t_vec[-1] + future_seconds
    t_future = t_vec[-1] + future_seconds
    pred_x = alpha_x * t_future + beta_x
    pred_y = alpha_y * t_future + beta_y

    return (int(pred_x), int(pred_y))


def refined_eigen_trajectory_prediction(trajectory, future_seconds, dt, weight=0.6):
    """
    将SVD预测和平滑速度预测做加权融合
    :param trajectory: 历史轨迹
    :param future_seconds: 预测未来秒数
    :param dt: 平均帧间隔
    :param weight: SVD预测的权重
    """
    pred_eigen = np.array(eigen_trajectory_prediction(trajectory, future_seconds, dt))
    pred_smooth = np.array(smooth_velocity_prediction(trajectory, future_seconds, dt, window_size=20))
    pred_final = weight * pred_eigen + (1 - weight) * pred_smooth
    return (int(pred_final[0]), int(pred_final[1]))


def play_webcam():
    #video_path = r"C:\Users\26375\Desktop\software\my table2\test_night.mp4"
    video_path = r"E:\challenge\realesrgan-ncnn-vulkan-20220424-windows\output_w_audio.mp4"
    vid_cap = cv2.VideoCapture(video_path)

    # 获取原视频的帧率和总帧数
    original_fps = vid_cap.get(cv2.CAP_PROP_FPS)
    frame_delay = 1.0 / original_fps  # 每帧应该的时间间隔
    total_frames = int(vid_cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"视频信息: {total_frames}帧, {original_fps}FPS, 预计时长: {total_frames / original_fps:.2f}秒")

    # 记录开始处理的时间
    video_start_time = time.time()
    frame_count = 0

    prev_time = time.time()
    fps_history = []

    while vid_cap.isOpened():
        # 计算这一帧的目标时间点（相对于视频开始时间）
        target_frame_time = frame_count * frame_delay

        # 记录这一帧开始处理的时间
        frame_start_time = time.time()

        success, frame = vid_cap.read()
        if not success:
            break

        current_time = time.time()
        dt_current = current_time - prev_time
        prev_time = current_time

        # dt_history 用于平滑 dt
        dt_history.append(dt_current)
        if len(dt_history) > 50:
            dt_history.pop(0)
        dt_avg = np.mean(dt_history)

        # YOLO 跟踪
        results = model.track(frame, persist=True, verbose=False, conf=conf_threshold)

        if results and len(results) > 0:
            annotated_frame = results[0].plot(font_size=0.5)
            boxes = results[0].boxes.xywh.cpu()

            if results[0].boxes.id is not None:
                track_ids = results[0].boxes.id.int().cpu().tolist()
            else:
                track_ids = []

            classes = results[0].boxes.cls.int().cpu().tolist()
            confidences = results[0].boxes.conf.cpu().tolist()

            for box, track_id, cls, conf_val in zip(boxes, track_ids, classes, confidences):
                # 针对非行人：低于阈值则跳过
                if cls != 0 and conf_val < conf_threshold:
                    continue

                # 针对行人（cls==0）的处理逻辑（例如绘制轨迹和预测点）
                if cls == 0:
                    x, y, _, _ = box
                    center = (float(x), float(y))
                    track_history[track_id].append(center)
                    if len(track_history[track_id]) > 50:
                        track_history[track_id].pop(0)
                    pts = np.array(track_history[track_id], dtype=np.int32).reshape((-1, 1, 2))
                    cv2.polylines(annotated_frame, [pts], isClosed=False, color=(0, 255, 0), thickness=2)
                    if len(track_history[track_id]) >= 5:
                        pred_1 = refined_eigen_trajectory_prediction(track_history[track_id], 1, dt_avg)
                        pred_2 = refined_eigen_trajectory_prediction(track_history[track_id], 2, dt_avg)
                        pred_3 = refined_eigen_trajectory_prediction(track_history[track_id], 3, dt_avg)
                        cv2.circle(annotated_frame, pred_1, 5, (0, 0, 255), -1)  # 红色
                        cv2.circle(annotated_frame, pred_2, 5, (0, 255, 255), -1)  # 黄色
                        cv2.circle(annotated_frame, pred_3, 5, (0, 255, 0), -1)  # 绿色
                else:
                    # 针对非行人且置信度达到要求的对象，绘制边框
                    x, y, w, h = box
                    cv2.rectangle(annotated_frame, (int(x - w / 2), int(y - h / 2)), (int(x + w / 2), int(y + h / 2)),
                                  (255, 0, 0), 2)

                # 发送 MQTT 消息
                client.publish("Group_99/IMAGE/predict", json.dumps({"confidence": conf_val}), qos=1)
                print("Confidence:", conf_val)
        else:
            annotated_frame = frame

        # 计算视频进度和时间同步信息
        elapsed_time = time.time() - video_start_time
        expected_time = frame_count / original_fps
        sync_diff = elapsed_time - expected_time

        # 计算处理耗时
        processing_time = time.time() - frame_start_time

        # 显示时间同步信息
        #elapsed_text = f'已播放: {elapsed_time:.2f}s / 预期: {expected_time:.2f}s / 差: {sync_diff:.2f}s'
        #cv2.putText(annotated_frame, elapsed_text, (10, 30),
        #           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        # 计算FPS并显示
        fps = 1 / dt_current if dt_current > 0 else 0
        fps_history.append(fps)
        if len(fps_history) > 50:
            fps_history.pop(0)
        avg_fps = sum(fps_history) / len(fps_history)
        fps_text = f'FPS: {fps:.1f}'
        #cv2.putText(annotated_frame, elapsed_text, (10, 30),
                    #           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        cv2.putText(annotated_frame, fps_text, (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.6, (255, 0, 0), 4)

        # 缩放后输出
        annotated_frame = cv2.resize(annotated_frame, (960, 540), interpolation=cv2.INTER_LINEAR)
        ret, jpeg = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            continue

        # 计算已经过去的实时时间
        elapsed_since_start = time.time() - video_start_time

        # 计算这一帧应该显示的时间点（基于帧序号和原始视频帧率）
        target_time = frame_count / original_fps

        # 计算需要等待的时间（如果处理太快）
        wait_time = max(0, target_time - elapsed_since_start)

        if wait_time > 0:
            time.sleep(wait_time)

        frame_bytes = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

        # 增加帧计数
        frame_count += 1

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