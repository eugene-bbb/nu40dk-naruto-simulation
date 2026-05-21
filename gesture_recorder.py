import argparse
import json
import os
import time
from datetime import datetime

import cv2
import mediapipe as mp


CAMERA_INDEX = 1
TEMPLATE_FILE = "gesture_templates.json"

REQUIRED_HANDS = 2
TARGET_SAMPLES = 20
CAPTURE_INTERVAL = 0.8
START_DELAY = 3.0

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


def load_templates():
    if not os.path.exists(TEMPLATE_FILE):
        return {}

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_templates(templates):
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)


def normalize_two_hand_landmarks(hand_landmarks_list):
    # 손목 x좌표 기준으로 왼쪽 손 → 오른쪽 손 순서 정렬
    sorted_hands = sorted(
        hand_landmarks_list,
        key=lambda hand: hand.landmark[0].x
    )

    points = []

    for hand in sorted_hands[:REQUIRED_HANDS]:
        for lm in hand.landmark:
            points.append([lm.x, lm.y, lm.z])

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    scale = max(max_x - min_x, max_y - min_y)

    if scale < 1e-6:
        scale = 1.0

    vector = []

    for x, y, z in points:
        nx = (x - center_x) / scale
        ny = (y - center_y) / scale
        nz = z / scale
        vector.extend([nx, ny, nz])

    return vector


def draw_text(frame, text, y, color=(255, 255, 255), scale=0.8):
    cv2.putText(
        frame,
        text,
        (30, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        2
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("gesture_name", help="저장할 손동작 이름. 예: CLONE")
    args = parser.parse_args()

    gesture_name = args.gesture_name.upper()

    templates = load_templates()

    if gesture_name not in templates:
        templates[gesture_name] = []

    # 기존 CLONE 샘플에 이어서 저장하고 싶지 않으면 아래 줄 주석 해제
    # templates[gesture_name] = []

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_AVFOUNDATION)

    if not cap.isOpened():
        print("Camera open failed")
        return

    print(f"Recording gesture: {gesture_name}")
    print(f"{START_DELAY}초 뒤 자동 저장을 시작합니다.")
    print("양손이 인식되면 자동으로 샘플이 저장됩니다.")
    print("종료하려면 q를 누르세요.")

    start_time = time.time()
    last_capture_time = 0

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as hands:

        while True:
            ret, frame = cap.read()

            if not ret:
                print("Frame read failed")
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            result = hands.process(rgb)

            hand_count = 0
            current_vector = None

            if result.multi_hand_landmarks:
                hand_count = len(result.multi_hand_landmarks)

                for hand_landmarks in result.multi_hand_landmarks:
                    mp_draw.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS
                    )

                if hand_count == REQUIRED_HANDS:
                    current_vector = normalize_two_hand_landmarks(
                        result.multi_hand_landmarks
                    )

            elapsed = time.time() - start_time
            sample_count = len(templates[gesture_name])

            draw_text(frame, f"Gesture: {gesture_name}", 40)
            draw_text(frame, f"Hands: {hand_count}/{REQUIRED_HANDS}", 80, (0, 255, 255))
            draw_text(frame, f"Saved: {sample_count}/{TARGET_SAMPLES}", 120, (0, 255, 0))

            if elapsed < START_DELAY:
                remain = START_DELAY - elapsed
                draw_text(
                    frame,
                    f"Get ready... {remain:.1f}s",
                    170,
                    (0, 200, 255),
                    1.0
                )
            else:
                draw_text(
                    frame,
                    "Auto recording ON",
                    170,
                    (0, 255, 0),
                    1.0
                )

                now = time.time()

                if (
                    current_vector is not None
                    and sample_count < TARGET_SAMPLES
                    and now - last_capture_time >= CAPTURE_INTERVAL
                ):
                    templates[gesture_name].append({
                        "vector": current_vector,
                        "hand_count": REQUIRED_HANDS,
                        "created_at": datetime.now().isoformat()
                    })

                    save_templates(templates)

                    last_capture_time = now

                    print(
                        f"Saved {gesture_name} sample "
                        f"#{len(templates[gesture_name])}"
                    )

                if len(templates[gesture_name]) >= TARGET_SAMPLES:
                    draw_text(
                        frame,
                        "Recording complete!",
                        220,
                        (0, 255, 0),
                        1.0
                    )

                    cv2.imshow("Gesture Recorder", frame)
                    cv2.waitKey(1500)
                    break

            draw_text(frame, "q: quit", 450, (200, 200, 200), 0.7)

            cv2.imshow("Gesture Recorder", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()

    save_templates(templates)

    print("Recording finished.")
    print(f"Total {gesture_name} samples: {len(templates[gesture_name])}")


if __name__ == "__main__":
    main()