/*  ================================================================
    MARS Project — Glove Firmware (Arduino Uno)
    Phase 1: Flex sensors only, no MPU-6050
    IMU values are fixed at 0,0,0 until MPU is connected.
    ================================================================
    Serial output (20 Hz):
      thumb,index,middle,ring,pinky,roll,pitch,yaw
      - flex values : 0-1023 raw ADC
      - roll/pitch/yaw : fixed 0.00 (no MPU yet)
    ================================================================ */

#define FLEX_THUMB  A0
#define FLEX_INDEX  A1
#define FLEX_MIDDLE A2
#define FLEX_RING   A3
#define FLEX_PINKY  A4

#define LOOP_MS 50   // 20 Hz

void setup() {
  Serial.begin(115200);
}

void loop() {
  unsigned long t0 = millis();

  int thumb  = analogRead(FLEX_THUMB);
  int index_ = analogRead(FLEX_INDEX);
  int middle = analogRead(FLEX_MIDDLE);
  int ring   = analogRead(FLEX_RING);
  int pinky  = analogRead(FLEX_PINKY);

  Serial.print(thumb);  Serial.print(',');
  Serial.print(index_); Serial.print(',');
  Serial.print(middle); Serial.print(',');
  Serial.print(ring);   Serial.print(',');
  Serial.print(pinky);  Serial.print(',');
  Serial.print(0.00);   Serial.print(',');  // roll  (no MPU)
  Serial.print(0.00);   Serial.print(',');  // pitch (no MPU)
  Serial.println(0.00);                     // yaw   (no MPU)

  unsigned long elapsed = millis() - t0;
  if (elapsed < LOOP_MS) delay(LOOP_MS - elapsed);
}