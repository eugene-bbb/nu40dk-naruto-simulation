import json
import math
import os


TEMPLATE_FILE = "gesture_templates.json"


def load_templates(template_file=TEMPLATE_FILE):
    if not os.path.exists(template_file):
        raise FileNotFoundError(
            f"{template_file} not found. 먼저 gesture_recorder.py로 손모양을 저장하세요."
        )

    with open(template_file, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_landmarks(hand_landmarks_list, max_hands=2):
    if not hand_landmarks_list:
        return None, 0

    sorted_hands = sorted(
        hand_landmarks_list[:max_hands],
        key=lambda hand: hand.landmark[0].x
    )

    points = []

    for hand in sorted_hands:
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

    return vector, len(sorted_hands)


def vector_distance(v1, v2):
    if len(v1) != len(v2):
        return float("inf")

    total = 0.0

    for a, b in zip(v1, v2):
        diff = a - b
        total += diff * diff

    return math.sqrt(total / len(v1))


def match_gesture(current_vector, current_hand_count, templates, threshold=0.09):
    best_name = "UNKNOWN"
    best_score = float("inf")

    for gesture_name, samples in templates.items():
        scores = []

        for sample in samples:
            sample_hand_count = sample.get("hand_count")

            if sample_hand_count is not None and sample_hand_count != current_hand_count:
                continue

            template_vector = sample["vector"]
            score = vector_distance(current_vector, template_vector)

            if score != float("inf"):
                scores.append(score)

        if not scores:
            continue

        scores.sort()

        top_k = scores[:5]
        avg_score = sum(top_k) / len(top_k)

        if avg_score < best_score:
            best_score = avg_score
            best_name = gesture_name

    if best_score <= threshold:
        return best_name, best_score

    return "UNKNOWN", best_score