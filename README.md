# MARS Project — Human Hand Mimic Robot

A glove equipped with flex sensors and an IMU that controls a simulated
robot hand in real time via ROS 2 and RViz.

You wear the glove, bend your fingers and move your wrist, and the 3D
hand model on screen mirrors every movement.


## Hardware Required

| Qty | Component | Purpose |
|-----|-----------|---------|
| 1 | Arduino Uno | Microcontroller |
| 5 | Flex sensors(2.2 inch) | One per finger (thumb, index, middle, ring, pinky) |
| 5 | 10 kOhm resistors | Voltage divider pull-downs for flex sensors |
| 1 | Breadboard | Prototyping connections |
| — | Jumper wires | Connections |
| 1 | Glove (fabric) | Mount sensors on fingers and wrist |
| 1 | USB A-to-B cable | Arduino to laptop |


## Software Required

| Software | Version | Purpose |
|----------|---------|---------|
| Arduino IDE | 1.8+ or 2.x | Upload firmware to Arduino |
| ROS 2 | Humble or newer | Robot middleware |
| Python 3 | 3.8+ | ROS 2 node runtime |
| pyserial | any | Serial communication (`pip install pyserial`) |
| rviz2 | (comes with ROS 2) | 3D visualisation |
| robot_state_publisher | (comes with ROS 2) | URDF to TF publisher |
| joint_state_publisher_gui | (comes with ROS 2) | Testing without hardware |

> ROS 2 runs on **Ubuntu Linux** or **WSL2 on Windows**.  The Arduino
> IDE runs on any OS.


## Project Structure

```
MARS Project/
├── README.md                    ← you are here
├── WIRING.md                    ← detailed wiring diagram & calibration
├── arduino/
│   └── glove_firmware/
│       └── glove_firmware.ino   ← Arduino sketch (reads sensors, sends serial)
└── ros2_ws/
    └── src/
        └── mars_hand/           ← ROS 2 Python package
            ├── package.xml
            ├── setup.py
            ├── setup.cfg
            ├── resource/mars_hand
            ├── mars_hand/
            │   ├── __init__.py
            │   └── serial_bridge.py   ← serial-to-ROS 2 bridge node
            ├── launch/
            │   └── display.launch.py  ← launch file (starts everything)
            ├── urdf/
            │   └── hand.urdf          ← robot hand model
            └── rviz/
                └── config.rviz        ← RViz display settings
```


## How It Works

```
┌──────────────┐   serial (USB)   ┌─────────────────┐   /joint_states   ┌───────┐
│  Arduino Uno │ ───────────────► │  serial_bridge │ ────────────────► │ RViz  │
│  (glove)     │  CSV @ 115200    │  (ROS 2 node)   │                   │       │
└──────────────┘                  └─────────────────┘                   └───────┘
  5 flex sensors                    maps raw ADC to                      shows the
                                    joint angles                         hand model
```

1. The **Arduino** reads 5 flex sensors and the MPU-6050 at 20 Hz and
   sends a CSV line over serial:
   `thumb,index,middle,ring,pinky,roll,pitch,yaw`

2. The **serial_bridge** ROS 2 node reads each line, converts raw
   sensor values into joint angles (radians), and publishes a
   `sensor_msgs/JointState` message.

3. **robot_state_publisher** reads the URDF and the joint states,
   computes the TF tree, and **RViz** renders the animated hand.


## Wiring Quick Reference

```
  Arduino Pin │ Connection
 ─────────────┼──────────────────────────────────
   A0         │ Thumb  flex sensor + 10kOhm → GND
   A1         │ Index  flex sensor + 10kOhm → GND
   A2         │ Middle flex sensor + 10kOhm → GND
   A3         │ Ring   flex sensor + 10kOhm → GND
   A4         │ Pinky  flex sensor + 10kOhm → GND
   5V         │ Flex sensor power
   GND        │ All grounds
```

Each flex sensor is wired as a voltage divider:
```
5V ── [Flex Sensor] ── junction ── Analog Pin
                          │
                       [10 kOhm]
                          │
                         GND
```

> **Why software I2C?** The Uno shares A4/A5 with hardware I2C.  The
> firmware bit-bangs I2C on D2/D3 so all five analog pins stay free.

See **[WIRING.md](WIRING.md)** for the full breadboard layout, MPU-6050
connections, pull-up resistor notes, and glove assembly tips.


## Step-by-Step Setup

### Step 1 — Wire the Hardware

Follow the wiring diagram in [WIRING.md](WIRING.md).  Double-check:
- Each flex sensor has its own 10 kOhm pull-down resistor
- MPU-6050 AD0 pin is connected to GND (sets address 0x68)
- No wires on A5 (it is unused)

### Step 2 — Upload Arduino Firmware

1. Open `arduino/glove_firmware/glove_firmware.ino` in the Arduino IDE.
2. Select **Board: Arduino Uno** and the correct **Port**.
3. Click **Upload**.
4. Open **Serial Monitor** at **115200 baud** — you should see CSV data
   streaming:
   ```
   512,480,495,501,488,0.00,0.00,0.00
   512,479,496,500,487,0.00,0.00,0.00
   ...
   ```
5. Bend each finger and verify the corresponding value changes.  Note
   the flat and bent values for calibration later.

### Step 3 — Build the ROS 2 Package

On your Ubuntu / WSL2 machine:

```bash
# create a workspace (skip if you already have one)
mkdir -p ~/mars_ws/src
cd ~/mars_ws

# copy the package into the workspace
cp -r /path/to/MARS\ Project/ros2_ws/src/mars_hand src/

# install Python dependency
pip install pyserial

# build
colcon build --packages-select mars_hand
source install/setup.bash
```

### Step 4 — Test Without Hardware (GUI Mode)

This launches RViz with slider controls for every joint — no Arduino
needed:

```bash
ros2 launch mars_hand display.launch.py gui:=true
```

You should see the robot hand in RViz.  Drag the sliders to verify
all fingers and the wrist move correctly.

### Step 5 — Run With the Glove

Plug the Arduino into your machine and find the serial port:

```bash
# Linux
ls /dev/ttyACM*    # usually /dev/ttyACM0

# WSL2 (requires usbipd-win to pass USB through)
ls /dev/ttyACM*
```

Launch:

```bash
ros2 launch mars_hand display.launch.py port:=/dev/ttyACM0
```

The hand in RViz should now mirror your glove movements in real time.

### Step 6 — Calibrate

For the most accurate tracking, calibrate the flex sensors:

1. Keep your hand **flat** — note the ADC value for each finger from
   the Serial Monitor (e.g. thumb=710, index=680, ...).
2. Make a **full fist** — note the ADC values (e.g. thumb=180,
   index=200, ...).
3. Pass these as launch arguments:

```bash
ros2 launch mars_hand display.launch.py \
    port:=/dev/ttyACM0 \
    thumb_flat:=710  thumb_bent:=180 \
    index_flat:=680  index_bent:=200 \
    middle_flat:=690 middle_bent:=195 \
    ring_flat:=700   ring_bent:=210 \
    pinky_flat:=670  pinky_bent:=190
```

For the IMU, hold your hand in the neutral pose and pass the resting
roll/pitch/yaw values:

```bash
    roll_offset:=3.5 pitch_offset:=-1.2 yaw_offset:=0.0
```


## Troubleshooting

| Problem | Solution |
|---------|----------|
| Serial Monitor shows nothing | Check baud rate is 115200; check USB cable; re-upload sketch |
| Values don't change when bending | Check flex sensor wiring — one end to 5V, other to analog pin + 10kOhm to GND |
| Permission denied on /dev/ttyACM0 | Run `sudo chmod 666 /dev/ttyACM0` or add yourself to the `dialout` group |
| WSL2 can't see the Arduino | Install [usbipd-win](https://github.com/dorssel/usbipd-win) to forward USB devices to WSL |
| Hand model is sideways in RViz | Set **Fixed Frame** to `forearm` in the RViz Displays panel |
| Fingers move in wrong direction | Swap the flat/bent calibration values for that finger |


## Joint Map

The URDF has 17 revolute joints controlled by 5 flex sensors + 1 IMU:

| Sensor | Drives Joints | Coupling |
|--------|--------------|----------|
| Thumb flex (A0) | `thumb_j1`, `thumb_pip` | Both proportional to flex |
| Index flex (A1) | `index_j1`, `index_pip`, `index_dip` | DIP = 67% of PIP |
| Middle flex (A2) | `middle_j1`, `middle_pip`, `middle_dip` | DIP = 67% of PIP |
| Ring flex (A3) | `ring_j1`, `ring_pip`, `ring_dip` | DIP = 67% of PIP |
| Pinky flex (A4) | `pinky_j1`, `pinky_pip`, `pinky_dip` | DIP = 67% of PIP |

