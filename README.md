# NU40DK Naruto Hand-Sign Jutsu Controller

> POV: You got into Ninja Academy, but it’s 2026.

This project turns Naruto-style hand signs into real hardware actions using a webcam, Python/OpenCV/MediaPipe, serial communication, NU40DK, dual OLED displays, and an external RGB LED.

When the camera recognizes a registered hand-sign sequence, Python sends a serial command to the NU40DK. The NU40DK then plays a matching OLED animation and RGB LED effect.

## Demo Features

- Real-time two-hand gesture recognition using MediaPipe Hands
- Template-based custom gesture recording
- Three jutsu triggers:
  - **Fireball Jutsu**
  - **Summoning Jutsu**
  - **Shadow Clone Jutsu**
- Dual 128×64 OLED output used as one logical **256×64 display**
- Dithered monochrome OLED animations to simulate grayscale/gradient effects
- External RGB LED effects synchronized with each animation
- Camera HUD showing hands, raw gesture, stable gesture, score, and current sequence

## Jutsu Commands

| Jutsu | Hand Sign Sequence | Serial Command |
|---|---|---|
| Fireball Jutsu | `SNAKE > RAM > MONKEY > BOAR > HORSE > TIGER` | `FIREBALL_JUTSU` |
| Summoning Jutsu | `BOAR > DOG > HEN > MONKEY > RAM` | `SUMMONING_JUTSU` |
| Shadow Clone Jutsu | `CLONE` | `SHADOW_CLONE` |

## Project Structure

```text
.
├── main_all_jutsu.py              # Main Python gesture-recognition controller
├── gesture_matcher.py             # Template loading, landmark normalization, gesture matching
├── gesture_recorder.py            # Tool for recording new gesture templates
├── gesture_templates.json         # Saved hand-sign template data
├── nu40-code/
│   ├── nu40-code.ino              # NU40DK Arduino sketch
│   ├── oled_animations.h          # Dual-OLED bitmap animation data
│   └── oled_logo.h                # Initial Naruto logo bitmap
└── oled_frames/                   # Source OLED animation frames
    ├── fireball/
    ├── clone/
    └── summon/
```

## Hardware

### Required Parts

- NU40DK board
- USB cable for programming and serial communication
- Webcam or laptop camera
- 2 × 128×64 I2C OLED displays
- 1 × 4-pin RGB LED or RGB LED module
- 3 × resistors for bare RGB LED, recommended **220Ω–330Ω** each
- Jumper wires

### OLED Wiring

The project uses two separate TWI/I2C instances so both OLEDs can use the same address, usually `0x3C`.

| Display | OLED Pin | NU40DK Pin |
|---|---|---|
| Left OLED | SDA | P0.07 |
| Left OLED | SCL/SCK | P0.08 |
| Right OLED | SDA | P0.09 |
| Right OLED | SCL/SCK | P0.10 |
| Both OLEDs | VCC/VDD | 3.3V |
| Both OLEDs | GND | GND |

The two OLEDs are treated as one logical 256×64 display:

```text
┌────────────────────┬────────────────────┐
│ Left OLED 128×64   │ Right OLED 128×64  │
│ x = 0..127         │ x = 128..255       │
└────────────────────┴────────────────────┘
```

### RGB LED Wiring

Current code uses these pins:

| RGB LED Pin | NU40DK Pin |
|---|---|
| R | P0.20 |
| G | P0.22 |
| B | P0.24 |
| GND / Common Cathode | GND |

If you use a bare 4-pin RGB LED, add a resistor to each color channel:

```text
P0.20 ─ 220Ω~330Ω ─ R
P0.22 ─ 220Ω~330Ω ─ G
P0.24 ─ 220Ω~330Ω ─ B
GND   ───────────── COM/GND
```

If your LED is common-anode, connect the common pin to 3.3V and set this in the Arduino code:

```cpp
const bool RGB_COMMON_ANODE = true;
```

For common-cathode modules, keep:

```cpp
const bool RGB_COMMON_ANODE = false;
```

## Software Requirements

### Python

Recommended: Python 3.10 or later.

Install dependencies:

```bash
pip install opencv-python mediapipe pyserial
```

### Arduino IDE

Install the NU40DK/nRF52 board package first, then install these libraries:

- `Adafruit GFX Library`
- `Adafruit SSD1306`
- `Adafruit TinyUSB Library`

## Setup

### 1. Upload NU40DK Firmware

Open this file in Arduino IDE:

```text
nu40-code/nu40-code.ino
```

Make sure these files are in the same sketch folder:

```text
nu40-code.ino
oled_animations.h
oled_logo.h
```

Upload to the NU40DK.

After upload, the OLED should show the initial Naruto logo. If the OLED does not display anything, check:

- OLED address: `0x3C` or `0x3D`
- SDA/SCL wiring
- 3.3V and GND
- Whether left/right OLEDs are connected to separate TWI pins

### 2. Run the Python Controller

From the project root:

```bash
python main_all_jutsu.py
```

The script will:

1. Load `gesture_templates.json`
2. Open the webcam
3. Find the NU40DK serial port automatically
4. Start hand-sign recognition
5. Send serial commands when a jutsu is detected

Press `q` in the camera window to quit.

## Recording New Gestures

Use `gesture_recorder.py` to add or update gesture templates.

Example:

```bash
python gesture_recorder.py DOG
python gesture_recorder.py HEN
python gesture_recorder.py CLONE
```

The recorder captures two-hand landmarks and appends samples to `gesture_templates.json`.

Default recording behavior:

- Required hands: 2
- Target samples per gesture: 20
- Capture interval: 0.8 seconds
- Start delay: 3 seconds

For best results:

- Keep both hands visible
- Avoid fully covering one hand with the other
- Record each sign from the same camera angle used during the demo
- Use strong lighting and a plain background

## How It Works

### Python Side

`main_all_jutsu.py` handles:

- Webcam capture
- MediaPipe hand landmark detection
- Gesture normalization
- Template matching
- Gesture stabilization
- Jutsu sequence detection
- Serial command transmission
- Camera HUD rendering

Gesture recognition flow:

```text
Camera Frame
    ↓
MediaPipe Hands
    ↓
Landmark Normalization
    ↓
Template Distance Matching
    ↓
Stable Gesture Filter
    ↓
Sequence Matcher
    ↓
Serial Command to NU40DK
```

### NU40DK Side

`nu40-code.ino` receives serial commands and plays matching outputs.

```text
Serial Command
    ↓
handleCommand()
    ↓
OLED Animation + RGB LED Effect
    ↓
Return to Idle Logo
```

## Tuning Parameters

### Camera Index

If the camera does not open, edit this in `main_all_jutsu.py`:

```python
CAMERA_INDEX = 1
```

Try:

```python
CAMERA_INDEX = 0
```

### Gesture Sensitivity

If gestures often show `UNKNOWN`, increase the threshold slightly:

```python
GESTURE_THRESHOLD = 0.11
```

Recommended range:

```python
0.10 ~ 0.13
```

If wrong gestures are detected too easily, lower the threshold.

### Stability

Main stability parameters:

```python
STABLE_HISTORY_SIZE = 9
STABLE_MIN_COUNT = 5
HOLD_LAST_GESTURE_TIME = 0.8
NO_HAND_RESET_TIME = 1.5
SEQUENCE_TIMEOUT = 8.0
```

If gestures flicker between `UNKNOWN` and a valid sign, increase `HOLD_LAST_GESTURE_TIME` slightly.

## Troubleshooting

### `NU40DK serial port not found`

Check that the board is connected and appears as a serial device.

On macOS, the port usually looks like:

```text
/dev/cu.usbmodemXXXX
/dev/cu.usbserialXXXX
```

### Camera does not open

Change:

```python
CAMERA_INDEX = 1
```

to:

```python
CAMERA_INDEX = 0
```

### OLED is blank

Check:

- OLED address: `0x3C` vs `0x3D`
- SDA/SCL wiring
- 3.3V power
- Whether both OLEDs are initialized successfully in Serial Monitor

### Left and right OLEDs show the same image

That means the sketch is not using split-frame dual-OLED output. Use the current `oled_animations.h` and `nu40-code.ino` version that draws left and right bitmap halves separately.

### Red channel of RGB LED does not work

Test the red channel with a simple blink/PWM sketch. If green and blue work but red never lights even after swapping wires and pins, the LED’s red channel is likely damaged.

### Bare RGB LED gets hot or too bright

Use resistors on R/G/B. Do not connect a bare RGB LED directly to GPIO without current-limiting resistors.

## Notes on Assets

This repository may contain Naruto-inspired names, visuals, and animation frames used for a personal hardware demo. If you publish the repository publicly, check whether you have the right to redistribute any anime-derived image or GIF assets. For a safer public release, replace copyrighted frames/logos with original pixel-art assets.

## Suggested GitHub Cleanup

Before pushing to GitHub, remove unnecessary generated/system files:

```bash
rm -rf .git
find . -name ".DS_Store" -delete
rm -rf __MACOSX
```

Recommended `.gitignore`:

```gitignore
.DS_Store
__MACOSX/
.venv/
__pycache__/
*.pyc
```

## Credits

Built with:

- Python
- OpenCV
- MediaPipe
- PySerial
- Arduino
- Adafruit SSD1306 / GFX
- NU40DK / nRF52840

## Short Description

A NU40DK-based Naruto hand-sign simulator that recognizes custom two-hand gestures with MediaPipe and triggers dual-OLED jutsu animations plus RGB LED effects through serial communication.
