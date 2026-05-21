#include <Adafruit_TinyUSB.h>                                                                
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include "oled_animations.h"
#include "oled_logo.h"  

const int LED1 = 13;
const int LED2 = 14;
const int LED3 = 15;
const int LED4 = 16;

const int RGB_R_PIN = 20;
const int RGB_G_PIN = 22;
const int RGB_B_PIN = 24;


const bool RGB_COMMON_ANODE = false;
const uint8_t RGB_MAX_BRIGHTNESS = 180;  // 0~255. Lower this if the LED is too bright.

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

// Verified dual OLED wiring on NU40DK
#define OLED0_SDA 7
#define OLED0_SCL 8
#define OLED1_SDA 9
#define OLED1_SCL 10

TwoWire wire0(
  NRF_TWIM0,
  NRF_TWIS0,
  SPIM0_SPIS0_TWIM0_TWIS0_SPI0_TWI0_IRQn,
  OLED0_SDA,
  OLED0_SCL
);

TwoWire wire1(
  NRF_TWIM1,
  NRF_TWIS1,
  SPIM1_SPIS1_TWIM1_TWIS1_SPI1_TWI1_IRQn,
  OLED1_SDA,
  OLED1_SCL
);

Adafruit_SSD1306 displayLeft(SCREEN_WIDTH, SCREEN_HEIGHT, &wire0, OLED_RESET);
Adafruit_SSD1306 displayRight(SCREEN_WIDTH, SCREEN_HEIGHT, &wire1, OLED_RESET);

String cmd = "";
bool leftOledReady = false;
bool rightOledReady = false;
bool oledReady = false;

void setup() {
  Serial.begin(115200);

  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);
  pinMode(LED3, OUTPUT);
  pinMode(LED4, OUTPUT);

  pinMode(RGB_R_PIN, OUTPUT);
  pinMode(RGB_G_PIN, OUTPUT);
  pinMode(RGB_B_PIN, OUTPUT);
  analogWriteResolution(8);

  allOff();
  rgbOff();

  wire0.begin();
  wire1.begin();
  wire0.setClock(400000);
  wire1.setClock(400000);

  leftOledReady = displayLeft.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS);
  rightOledReady = displayRight.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS);
  oledReady = leftOledReady || rightOledReady;

  if (!leftOledReady) Serial.println("Left OLED failed");
  if (!rightOledReady) Serial.println("Right OLED failed");

  if (leftOledReady) {
    displayLeft.clearDisplay();
    displayLeft.setTextColor(SSD1306_WHITE);
    displayLeft.setCursor(0, 0);
    displayLeft.println("LEFT OLED");
    displayLeft.display();
  }

  if (rightOledReady) {
    displayRight.clearDisplay();
    displayRight.setTextColor(SSD1306_WHITE);
    displayRight.setCursor(0, 0);
    displayRight.println("RIGHT OLED");
    displayRight.display();
  }

  delay(800);
  showIdleScreen();

  Serial.println("NU40DK Dual OLED Spell Receiver Ready - RGB fixed");
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      cmd.trim();
      if (cmd.length() > 0) {
        handleCommand(cmd);
      }
      cmd = "";
    } else {
      cmd += c;
    }
  }
}

void handleCommand(String command) {
  Serial.print("Received: ");
  Serial.println(command);

  if (command == "READY") {
    showText("READY");
    readyEffect();
  }
  else if (command == "CHARGE") {
    showText("CHARGE");
    chargeEffect();
  }
  else if (command == "FIRE") {
    showText("FIRE");
    fireEffect();
  }
  else if (command == "RESET") {
    allOff();
    rgbOff();
    showIdleScreen();
  }
  else if (command == "ULTIMATE_FIRE") {
    showText("ULTIMATE FIRE");
    ultimateFireEffect();
  }
  else if (command == "QUICK_FIRE") {
    showText("QUICK FIRE");
    fireEffect();
  }
  else if (command == "POWER_FIRE") {
    showText("POWER FIRE");
    powerFireEffect();
  }
  else if (command == "SHADOW_CLONE") {
    playCloneAnimation();
    shadowCloneEffect();
    rgbOff();
    showIdleScreen();
  }
  else if (command == "FIREBALL_JUTSU") {
    playFireballAnimation();
    fireballEffect();
    rgbOff();
    showIdleScreen();
  }
  else if (command == "SUMMONING_JUTSU") {
    playSummonAnimation();
    summoningJutsuEffect();
    rgbOff();
    showIdleScreen();
  }
  else {
    showText("UNKNOWN CMD");
  }
}

const uint8_t RGB_MODE_NONE = 0;
const uint8_t RGB_MODE_FIREBALL = 1;
const uint8_t RGB_MODE_CLONE = 2;
const uint8_t RGB_MODE_SUMMON = 3;

uint8_t scaleRgb(uint8_t value) {
  return (uint16_t)value * RGB_MAX_BRIGHTNESS / 255;
}

void writeRgbChannel(int pin, uint8_t value) {
  uint8_t scaled = scaleRgb(value);

  if (RGB_COMMON_ANODE) {
    analogWrite(pin, 255 - scaled);
  } else {
    analogWrite(pin, scaled);
  }
}

void setRgbColor(uint8_t r, uint8_t g, uint8_t b) {
  writeRgbChannel(RGB_R_PIN, r);
  writeRgbChannel(RGB_G_PIN, g);
  writeRgbChannel(RGB_B_PIN, b);
}

void rgbOff() {
  setRgbColor(0, 0, 0);
}

void updateRgbForAnimation(uint8_t mode, uint16_t frameIndex, uint16_t frameCount) {
  switch (mode) {
    case RGB_MODE_FIREBALL:
      // Fireball: red -> orange -> yellow flicker
      switch (frameIndex % 5) {
        case 0: setRgbColor(0, 235, 255); break;    // deep red
        case 1: setRgbColor(0, 200, 255); break;    // orange-red
        case 2: setRgbColor(0, 100, 255); break;   // orange
        //case 3: setRgbColor(0, 35, 225); break;  // yellow flash
        default: setRgbColor(0, 165, 255); break;
      }
      break;

    case RGB_MODE_CLONE:
      // Shadow clone: blue/cyan/white chakra-like flashes
      switch (frameIndex % 6) {
        case 0: setRgbColor(150, 100, 0); break;      // blue
        case 2: setRgbColor(150, 0, 0); break;     // cyan
        case 1: setRgbColor(150, 70, 0); break;     // sky blue
        case 3: setRgbColor(35, 0, 0); break;   // white flash
        case 4: setRgbColor(255, 135, 0); break;
        default: setRgbColor(255, 255, 175); break;       // dark blue
      }
      break;
      
    case RGB_MODE_SUMMON:
      // Summoning: blood red at the beginning, then blue/white/purple energy
      if (frameIndex < frameCount / 5) {
        setRgbColor(255, 0, 0);                       // blood mark
      } else {
        switch (frameIndex % 6) {
          case 0: setRgbColor(255, 175, 0); break;     // blue
          case 1: setRgbColor(255, 35, 0); break;    // cyan
          case 2: setRgbColor(75, 255, 0); break;    // purple
          case 3: setRgbColor(0, 0, 0); break;  // white flash
          case 4: setRgbColor(175, 255, 0); break;     // violet
          default: setRgbColor(255, 95, 0); break;
        }
      }
      break;

    default:
      rgbOff();
      break;
  }
}

void drawDualFrame(const uint8_t* leftFrame, const uint8_t* rightFrame) {
  if (!oledReady) return;

  if (leftOledReady) {
    displayLeft.clearDisplay();
    displayLeft.drawBitmap(0, 0, leftFrame, OLED_ANIM_WIDTH, OLED_ANIM_HEIGHT, SSD1306_WHITE);
  }

  if (rightOledReady) {
    displayRight.clearDisplay();
    displayRight.drawBitmap(0, 0, rightFrame, OLED_ANIM_WIDTH, OLED_ANIM_HEIGHT, SSD1306_WHITE);
  }

  if (leftOledReady) displayLeft.display();
  if (rightOledReady) displayRight.display();
}

void playDualAnimation(
  const uint8_t* const framesLeft[],
  const uint8_t* const framesRight[],
  uint16_t frameCount,
  uint16_t frameDelayMs,
  uint8_t repeatCount,
  uint8_t rgbMode
) {
  if (!oledReady) return;

  for (uint8_t repeat = 0; repeat < repeatCount; repeat++) {
    for (uint16_t i = 0; i < frameCount; i++) {
      updateRgbForAnimation(rgbMode, i, frameCount);
      drawDualFrame(framesLeft[i], framesRight[i]);
      delay(frameDelayMs);
    }
  }
}

void playFireballAnimation() {
  playDualAnimation(fireballFramesLeft, fireballFramesRight, fireballFrameCount, 80, 1, RGB_MODE_FIREBALL);
}

void playCloneAnimation() {
  playDualAnimation(cloneFramesLeft, cloneFramesRight, cloneFrameCount, 85, 1, RGB_MODE_CLONE);
}

void playSummonAnimation() {
  playDualAnimation(summonFramesLeft, summonFramesRight, summonFrameCount, 70, 1, RGB_MODE_SUMMON);
}

void showText(const char* text) {
  if (!oledReady) return;

  if (leftOledReady) {
    displayLeft.clearDisplay();
    displayLeft.setTextColor(SSD1306_WHITE);
    displayLeft.setTextSize(1);
    displayLeft.setCursor(0, 0);
    displayLeft.println("NUCODE JUTSU");
    displayLeft.drawLine(0, 12, 127, 12, SSD1306_WHITE);
    displayLeft.setTextSize(2);
    displayLeft.setCursor(0, 28);
    displayLeft.println(text);
    displayLeft.display();
  }

  if (rightOledReady) {
    displayRight.clearDisplay();
    displayRight.setTextColor(SSD1306_WHITE);
    displayRight.setTextSize(1);
    displayRight.setCursor(0, 0);
    displayRight.println("DUAL OLED");
    displayRight.drawLine(0, 12, 127, 12, SSD1306_WHITE);
    displayRight.setTextSize(2);
    displayRight.setCursor(0, 28);
    displayRight.println(text);
    displayRight.display();
  }
}

void showIdleScreen() {
  if (!oledReady) return;

  if (leftOledReady) {
    displayLeft.clearDisplay();
    displayLeft.drawBitmap(0, 0, narutoLogoLeft, NARUTO_LOGO_WIDTH, NARUTO_LOGO_HEIGHT, SSD1306_WHITE);
    displayLeft.display();
  }

  if (rightOledReady) {
    displayRight.clearDisplay();
    displayRight.drawBitmap(0, 0, narutoLogoRight, NARUTO_LOGO_WIDTH, NARUTO_LOGO_HEIGHT, SSD1306_WHITE);
    displayRight.display();
  }
}

void summoningJutsuEffect() {
  for (int round = 0; round < 4; round++) {
    digitalWrite(LED1, HIGH); delay(50);
    digitalWrite(LED2, HIGH); delay(50);
    digitalWrite(LED3, HIGH); delay(50);
    digitalWrite(LED4, HIGH); delay(50);
    allOff(); delay(50);
  }

  for (int i = 0; i < 15; i++) {
    allOn(); delay(35);
    allOff(); delay(35);
  }

  allOn(); delay(700);
  allOff();
}

void fireballEffect() {
  for (int round = 0; round < 4; round++) {
    digitalWrite(LED1, HIGH); delay(50);
    digitalWrite(LED2, HIGH); delay(50);
    digitalWrite(LED3, HIGH); delay(50);
    digitalWrite(LED4, HIGH); delay(50);
    allOff(); delay(50);
  }

  for (int i = 0; i < 15; i++) {
    allOn(); delay(35);
    allOff(); delay(35);
  }

  allOn(); delay(700);
  allOff();
}

void ultimateFireEffect() {
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED1, HIGH); delay(80);
    digitalWrite(LED2, HIGH); delay(80);
    digitalWrite(LED3, HIGH); delay(80);
    digitalWrite(LED4, HIGH); delay(80);
    allOff(); delay(80);
  }

  for (int i = 0; i < 15; i++) {
    allOn(); delay(40);
    allOff(); delay(40);
  }

  allOn();
}

void shadowCloneEffect() {
  for (int round = 0; round < 3; round++) {
    digitalWrite(LED1, HIGH); delay(60);
    digitalWrite(LED2, HIGH); delay(60);
    digitalWrite(LED3, HIGH); delay(60);
    digitalWrite(LED4, HIGH); delay(60);
    allOff(); delay(80);
  }

  for (int i = 0; i < 12; i++) {
    digitalWrite(LED1, HIGH);
    digitalWrite(LED3, HIGH);
    digitalWrite(LED2, LOW);
    digitalWrite(LED4, LOW);
    delay(50);

    digitalWrite(LED1, LOW);
    digitalWrite(LED3, LOW);
    digitalWrite(LED2, HIGH);
    digitalWrite(LED4, HIGH);
    delay(50);
  }

  allOff();
}

void powerFireEffect() {
  for (int i = 0; i < 8; i++) {
    digitalWrite(LED1, HIGH);
    digitalWrite(LED3, HIGH);
    delay(80);
    digitalWrite(LED1, LOW);
    digitalWrite(LED3, LOW);

    digitalWrite(LED2, HIGH);
    digitalWrite(LED4, HIGH);
    delay(80);
    digitalWrite(LED2, LOW);
    digitalWrite(LED4, LOW);
  }
}

void readyEffect() {
  allOff();
  digitalWrite(LED1, HIGH);
}

void chargeEffect() {
  allOff();

  for (int i = 0; i < 4; i++) {
    digitalWrite(LED1, HIGH); delay(100);
    digitalWrite(LED2, HIGH); delay(100);
    digitalWrite(LED3, HIGH); delay(100);
    digitalWrite(LED4, HIGH); delay(100);
    allOff(); delay(100);
  }
}

void fireEffect() {
  for (int i = 0; i < 10; i++) {
    allOn(); delay(50);
    allOff(); delay(50);
  }

  digitalWrite(LED4, HIGH);
}

void allOn() {
  digitalWrite(LED1, HIGH);
  digitalWrite(LED2, HIGH);
  digitalWrite(LED3, HIGH);
  digitalWrite(LED4, HIGH);
}

void allOff() {
  digitalWrite(LED1, LOW);
  digitalWrite(LED2, LOW);
  digitalWrite(LED3, LOW);
  digitalWrite(LED4, LOW);
}
