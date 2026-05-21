import time
from collections import deque, Counter

import cv2
import mediapipe as mp
import serial
from serial.tools import list_ports

from gesture_matcher import (
    load_templates,
    normalize_landmarks,
    match_gesture,
)


CAMERA_INDEX = 1
BAUD = 115200

MAX_HANDS = 2
REQUIRED_HANDS = 2

GESTURE_THRESHOLD = 0.11

STABLE_HISTORY_SIZE = 9
STABLE_MIN_COUNT = 5
HOLD_LAST_GESTURE_TIME = 0.8
NO_HAND_RESET_TIME = 1.5

SEQUENCE_TIMEOUT = 8.0
SEND_COOLDOWN = 3.0

SPELLS = {
    ("SNAKE", "RAM", "MONKEY", "BOAR", "HORSE", "TIGER"): {
        "name": "Fireball Jutsu",
        "command": "FIREBALL_JUTSU",
    },
    ("BOAR", "DOG", "HEN", "MONKEY", "RAM"): {
        "name": "Summoning Jutsu",
        "command": "SUMMONING_JUTSU",
    },
}

INSTANT_GESTURE_COMMANDS = {
    "CLONE": {
        "name": "Shadow Clone",
        "command": "SHADOW_CLONE",
    },
}

SEQUENCE_GESTURES = sorted({gesture for pattern in SPELLS.keys() for gesture in pattern})
ALL_TARGET_GESTURES = set(SEQUENCE_GESTURES) | set(INSTANT_GESTURE_COMMANDS.keys())
MAX_PATTERN_LENGTH = max(len(pattern) for pattern in SPELLS.keys())

gesture_history = deque(maxlen=STABLE_HISTORY_SIZE)

last_valid_gesture = "NO_HAND"
last_valid_score = 999.0
last_valid_time = 0

gesture_sequence = []
last_added_gesture = None
last_gesture_time = 0

last_sent_times = {}

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


def find_serial_port():
    ports = list(list_ports.comports())

    print("Available ports:")
    for p in ports:
        print(f"- {p.device} | {p.description}")

    candidates = [
        p.device for p in ports
        if "usbmodem" in p.device or "usbserial" in p.device
    ]

    if not candidates:
        raise RuntimeError("NU40DK serial port not found.")

    return candidates[0]


def get_stable_gesture(current_gesture, score):
    global last_valid_gesture, last_valid_score, last_valid_time

    now = time.time()

    if current_gesture in ["UNKNOWN", "NO_HAND", "NEED_TWO_HANDS"]:
        if now - last_valid_time <= HOLD_LAST_GESTURE_TIME:
            return last_valid_gesture

        gesture_history.clear()
        return current_gesture

    if current_gesture not in ALL_TARGET_GESTURES:
        if now - last_valid_time <= HOLD_LAST_GESTURE_TIME:
            return last_valid_gesture

        gesture_history.clear()
        return "UNKNOWN"

    gesture_history.append(current_gesture)

    counter = Counter(gesture_history)
    gesture, count = counter.most_common(1)[0]

    if count >= STABLE_MIN_COUNT:
        last_valid_gesture = gesture
        last_valid_score = score
        last_valid_time = now
        return gesture

    if now - last_valid_time <= HOLD_LAST_GESTURE_TIME:
        return last_valid_gesture

    return "STABILIZING"


def reset_sequence():
    global gesture_sequence, last_added_gesture, last_gesture_time

    gesture_sequence = []
    last_added_gesture = None
    last_gesture_time = 0


def is_prefix_of_any_spell(sequence):
    seq_tuple = tuple(sequence)

    for pattern in SPELLS.keys():
        if pattern[:len(seq_tuple)] == seq_tuple:
            return True

    return False


def update_sequence(stable_gesture):
    global gesture_sequence, last_added_gesture, last_gesture_time

    now = time.time()

    if last_gesture_time != 0 and now - last_gesture_time > SEQUENCE_TIMEOUT:
        print("sequence timeout -> reset")
        reset_sequence()

    if stable_gesture not in SEQUENCE_GESTURES:
        return None

    if stable_gesture == last_added_gesture:
        return None

    gesture_sequence.append(stable_gesture)
    last_added_gesture = stable_gesture
    last_gesture_time = now

    if len(gesture_sequence) > MAX_PATTERN_LENGTH:
        gesture_sequence = gesture_sequence[-MAX_PATTERN_LENGTH:]

    print("sequence:", " > ".join(gesture_sequence))

    for pattern, info in SPELLS.items():
        pattern_length = len(pattern)

        if tuple(gesture_sequence[-pattern_length:]) == pattern:
            print("spell matched:", info["name"], "->", info["command"])
            reset_sequence()
            return info["command"]

    if not is_prefix_of_any_spell(gesture_sequence):
        print("wrong sequence -> reset")
        current = stable_gesture
        reset_sequence()

        # 현재 손동작이 어떤 술법의 첫 동작이면 그 동작부터 다시 시작
        if any(pattern[0] == current for pattern in SPELLS.keys()):
            gesture_sequence.append(current)
            last_added_gesture = current
            last_gesture_time = now
            print("sequence:", " > ".join(gesture_sequence))

    return None


def send_command(ser, command):
    now = time.time()
    last_time = last_sent_times.get(command, 0)

    if now - last_time < SEND_COOLDOWN:
        return

    ser.write((command + "\n").encode("utf-8"))
    ser.flush()
    last_sent_times[command] = now
    print("send:", command)


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


def draw_transparent_rect(frame, x1, y1, x2, y2, color, alpha=0.45):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def draw_hud_text(frame, text, x, y, color=(255, 255, 255), scale=0.6, thickness=2):
    cv2.putText(
        frame,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA
    )


def draw_sequence_boxes(frame, sequence):
    x = 30
    y = 215

    if not sequence:
        draw_hud_text(frame, "EMPTY", x, y + 25, (120, 120, 120), 0.55, 2)
        return

    for idx, gesture in enumerate(sequence):
        box_x = x + idx * 105

        draw_transparent_rect(
            frame,
            box_x,
            y,
            box_x + 95,
            y + 38,
            (0, 0, 0),
            0.60
        )

        cv2.rectangle(
            frame,
            (box_x, y),
            (box_x + 95, y + 38),
            (0, 220, 255),
            2
        )

        draw_hud_text(
            frame,
            gesture,
            box_x + 8,
            y + 25,
            (0, 255, 255),
            0.48,
            2
        )


def draw_available_jutsu(frame):
    h, w = frame.shape[:2]

    panel_x1 = max(w - 335, 330)
    panel_y1 = 60
    panel_x2 = w - 25
    panel_y2 = 235

    draw_transparent_rect(frame, panel_x1, panel_y1, panel_x2, panel_y2, (0, 0, 0), 0.62)
    cv2.rectangle(frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (120, 120, 120), 1)

    draw_hud_text(frame, "AVAILABLE JUTSU", panel_x1 + 15, panel_y1 + 28, (255, 255, 255), 0.58, 2)

    draw_hud_text(frame, "1. FIREBALL", panel_x1 + 15, panel_y1 + 58, (0, 120, 255), 0.52, 2)
    draw_hud_text(frame, "SNAKE > RAM > MONKEY > BOAR > HORSE > TIGER", panel_x1 + 15, panel_y1 + 80, (180, 180, 180), 0.34, 1)

    draw_hud_text(frame, "2. SUMMONING", panel_x1 + 15, panel_y1 + 108, (255, 80, 180), 0.52, 2)
    draw_hud_text(frame, "BOAR > DOG > HEN > MONKEY > RAM", panel_x1 + 15, panel_y1 + 130, (180, 180, 180), 0.34, 1)

    draw_hud_text(frame, "3. SHADOW CLONE", panel_x1 + 15, panel_y1 + 158, (255, 180, 80), 0.52, 2)


def draw_status(frame, hand_count, raw_gesture, stable_gesture, best_score):
    h, w = frame.shape[:2]

    # 전체 테두리
    cv2.rectangle(frame, (8, 8), (w - 8, h - 8), (0, 255, 255), 2)

    # 상단 타이틀 바
    draw_transparent_rect(frame, 15, 15, w - 15, 48, (0, 0, 0), 0.65)
    draw_hud_text(frame, "NARUTO", 30, 39, (0, 255, 255), 0.72, 2)

    # 왼쪽 상태 패널
    draw_transparent_rect(frame, 20, 60, 315, 255, (0, 0, 0), 0.62)
    cv2.rectangle(frame, (20, 60), (315, 255), (120, 120, 120), 1)

    draw_hud_text(frame, f"HANDS  : {hand_count}/{REQUIRED_HANDS}", 35, 90, (0, 255, 255), 0.6, 2)
    draw_hud_text(frame, f"RAW    : {raw_gesture}", 35, 120, (255, 255, 255), 0.6, 2)
    draw_hud_text(frame, f"STABLE : {stable_gesture}", 35, 150, (0, 255, 0), 0.6, 2)
    draw_hud_text(frame, f"SCORE  : {best_score:.3f}", 35, 180, (0, 200, 255), 0.6, 2)

    # 시퀀스 표시
    draw_hud_text(frame, "SEQUENCE", 30, 207, (255, 255, 255), 0.58, 2)
    draw_sequence_boxes(frame, gesture_sequence)

    # 오른쪽 술법 목록
    draw_available_jutsu(frame)

    # 하단 안내
    draw_transparent_rect(frame, 20, h - 45, w - 20, h - 15, (0, 0, 0), 0.58)
    draw_hud_text(
        frame,
        "q: quit   |   Hold each sign until STABLE changes",
        35,
        h - 23,
        (200, 200, 200),
        0.52,
        1
    )


def main():
    templates = load_templates()
    print("Loaded gestures:", list(templates.keys()))

    missing = sorted(ALL_TARGET_GESTURES - set(templates.keys()))
    if missing:
        print("WARNING: missing gesture templates:", missing)

    port = find_serial_port()
    print("Using serial port:", port)

    ser = serial.Serial(port, BAUD, timeout=1)
    time.sleep(2)

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_AVFOUNDATION)

    if not cap.isOpened():
        print("Camera open failed")
        ser.close()
        return

    last_hand_seen_time = 0

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=MAX_HANDS,
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    ) as hands:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("Frame read failed")
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            result = hands.process(rgb)

            raw_gesture = "NO_HAND"
            stable_gesture = "NO_HAND"
            best_score = 999.0
            hand_count = 0
            now = time.time()

            if result.multi_hand_landmarks:
                hand_count = len(result.multi_hand_landmarks)

                for hand_landmarks in result.multi_hand_landmarks:
                    mp_draw.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS
                    )

                if hand_count >= REQUIRED_HANDS:
                    last_hand_seen_time = now

                    current_vector, current_hand_count = normalize_landmarks(
                        result.multi_hand_landmarks,
                        max_hands=MAX_HANDS
                    )

                    if current_vector is not None and current_hand_count >= REQUIRED_HANDS:
                        raw_gesture, best_score = match_gesture(
                            current_vector,
                            current_hand_count,
                            templates,
                            threshold=GESTURE_THRESHOLD
                        )

                        stable_gesture = get_stable_gesture(raw_gesture, best_score)
                    else:
                        raw_gesture = "NEED_TWO_HANDS"
                        stable_gesture = get_stable_gesture(raw_gesture, best_score)
                else:
                    raw_gesture = "NEED_TWO_HANDS"
                    stable_gesture = get_stable_gesture(raw_gesture, best_score)
            else:
                raw_gesture = "NO_HAND"
                stable_gesture = get_stable_gesture(raw_gesture, best_score)

                if last_hand_seen_time != 0 and now - last_hand_seen_time > NO_HAND_RESET_TIME:
                    stable_gesture = "RESET"
                    reset_sequence()
                    send_command(ser, "RESET")

            # 단일 동작 술법: 분신술
            if stable_gesture in INSTANT_GESTURE_COMMANDS:
                command = INSTANT_GESTURE_COMMANDS[stable_gesture]["command"]
                reset_sequence()
                send_command(ser, command)

            # 시퀀스 술법: 호화구 / 소환술
            else:
                spell_command = update_sequence(stable_gesture)
                if spell_command is not None:
                    send_command(ser, spell_command)

            while ser.in_waiting:
                line = ser.readline().decode(errors="ignore").strip()
                if line:
                    print("board:", line)

            draw_status(frame, hand_count, raw_gesture, stable_gesture, best_score)

            cv2.imshow("All Jutsu Gesture Controller", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    ser.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
