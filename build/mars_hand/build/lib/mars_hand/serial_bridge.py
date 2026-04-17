"""
MARS Project — Serial-to-ROS 2 Bridge Node
===========================================
Reads CSV frames from the Arduino glove over serial and publishes
sensor_msgs/JointState so that robot_state_publisher + RViz can
animate the hand URDF in real time.

Serial format (from Arduino):
    thumb,index,middle,ring,pinky,roll,pitch,yaw\n
    - flex values : 0-1023 raw ADC
    - roll/pitch  : degrees (complementary-filtered)
    - yaw         : degrees (gyro-integrated)

Published topic:
    /joint_states  (sensor_msgs/msg/JointState)
"""

import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import serial


class SerialBridge(Node):
    def __init__(self):
        super().__init__('serial_bridge')

        # ---- parameters (all overridable via launch / CLI) ----
        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baud', 115200)

        # flex sensor calibration: [flat_adc, bent_adc] per finger
        # Measure YOUR sensors and update these — the defaults are
        # reasonable starting points for common flex sensors.
        self.declare_parameter('thumb_flat',  700)
        self.declare_parameter('thumb_bent',  200)
        self.declare_parameter('index_flat',  700)
        self.declare_parameter('index_bent',  200)
        self.declare_parameter('middle_flat', 700)
        self.declare_parameter('middle_bent', 200)
        self.declare_parameter('ring_flat',   700)
        self.declare_parameter('ring_bent',   200)
        self.declare_parameter('pinky_flat',  700)
        self.declare_parameter('pinky_bent',  200)

        # wrist IMU rest-pose offsets (degrees) — set these to the
        # roll/pitch/yaw the MPU reads when the hand is in its
        # neutral position so the model starts centred.
        self.declare_parameter('roll_offset',  0.0)
        self.declare_parameter('pitch_offset', 0.0)
        self.declare_parameter('yaw_offset',   0.0)

        port = self.get_parameter('port').value
        baud = self.get_parameter('baud').value

        # ---- calibration values ----
        self.cal = {
            'thumb':  (self.get_parameter('thumb_flat').value,
                       self.get_parameter('thumb_bent').value),
            'index':  (self.get_parameter('index_flat').value,
                       self.get_parameter('index_bent').value),
            'middle': (self.get_parameter('middle_flat').value,
                       self.get_parameter('middle_bent').value),
            'ring':   (self.get_parameter('ring_flat').value,
                       self.get_parameter('ring_bent').value),
            'pinky':  (self.get_parameter('pinky_flat').value,
                       self.get_parameter('pinky_bent').value),
        }
        self.roll_off  = self.get_parameter('roll_offset').value
        self.pitch_off = self.get_parameter('pitch_offset').value
        self.yaw_off   = self.get_parameter('yaw_offset').value

        # ---- joint names (must match URDF exactly) ----
        self.joint_names = [
            # wrist (3)
            'wrist_yaw', 'wrist_pitch', 'wrist_dev',
            # thumb (2)
            'thumb_j1', 'thumb_pip',
            # index (3)
            'index_j1', 'index_pip', 'index_dip',
            # middle (3)
            'middle_j1', 'middle_pip', 'middle_dip',
            # ring (3)
            'ring_j1', 'ring_pip', 'ring_dip',
            # pinky (3)
            'pinky_j1', 'pinky_pip', 'pinky_dip',
        ]

        # ---- joint limits from URDF [lower, upper] in radians ----
        self.limits = {
            'wrist_yaw':   (-1.50,  1.50),
            'wrist_pitch': (-0.87,  0.87),
            'wrist_dev':   (-0.35,  0.35),
            'thumb_j1':    (-1.20,  0.30),
            'thumb_pip':   (-0.80,  0.00),
            'index_j1':    ( 0.00,  0.90),
            'index_pip':   ( 0.00,  1.20),
            'index_dip':   ( 0.00,  0.80),
            'middle_j1':   ( 0.00,  0.90),
            'middle_pip':  ( 0.00,  1.20),
            'middle_dip':  ( 0.00,  0.80),
            'ring_j1':     ( 0.00,  0.90),
            'ring_pip':    ( 0.00,  1.20),
            'ring_dip':    ( 0.00,  0.80),
            'pinky_j1':    ( 0.00,  0.90),
            'pinky_pip':   ( 0.00,  1.20),
            'pinky_dip':   ( 0.00,  0.80),
        }

        # ---- serial port ----
        try:
            self.ser = serial.Serial(port, baud, timeout=0.1)
            self.get_logger().info(f'Opened {port} @ {baud}')
        except serial.SerialException as e:
            self.get_logger().error(f'Cannot open {port}: {e}')
            raise SystemExit(1)

        # ---- publisher ----
        self.pub = self.create_publisher(JointState, 'joint_states', 10)

        # timer at 30 Hz (faster than Arduino's 20 Hz to avoid lag)
        self.timer = self.create_timer(1.0 / 30.0, self.timer_cb)
        self.get_logger().info('serial_bridge started')

    # ----------------------------------------------------------------
    #  Flex sensor → normalised 0..1  (0 = flat, 1 = fully bent)
    # ----------------------------------------------------------------
    def flex_normalise(self, raw: int, finger: str) -> float:
        flat_val, bent_val = self.cal[finger]
        if flat_val == bent_val:
            return 0.0
        norm = (flat_val - raw) / (flat_val - bent_val)
        return max(0.0, min(1.0, norm))

    # ----------------------------------------------------------------
    #  Map one finger's flex (0..1) to its 3 joint angles (or 2 for thumb)
    # ----------------------------------------------------------------
    @staticmethod
    def finger_joints(flex: float, j1_lim, pip_lim, dip_lim=None):
        """Return (j1, pip[, dip]) angles.  Coupling ratios mimic a
        real hand: MCP leads, PIP follows fully, DIP ~ 67 % of PIP."""
        j1  = j1_lim[0]  + flex * (j1_lim[1]  - j1_lim[0])
        pip = pip_lim[0] + flex * (pip_lim[1] - pip_lim[0])
        if dip_lim is not None:
            dip = dip_lim[0] + flex * 0.67 * (dip_lim[1] - dip_lim[0])
            return j1, pip, dip
        return j1, pip

    # ----------------------------------------------------------------
    #  Clamp helper
    # ----------------------------------------------------------------
    def clamp(self, name: str, val: float) -> float:
        lo, hi = self.limits[name]
        return max(lo, min(hi, val))

    # ----------------------------------------------------------------
    #  Timer callback — read serial, map, publish
    # ----------------------------------------------------------------
    def timer_cb(self):
        line = b''
        try:
            line = self.ser.readline()
        except serial.SerialException:
            return
        if not line:
            return

        try:
            parts = line.decode('ascii', errors='ignore').strip().split(',')
            if len(parts) != 8:
                return
            thumb_raw  = int(parts[0])
            index_raw  = int(parts[1])
            middle_raw = int(parts[2])
            ring_raw   = int(parts[3])
            pinky_raw  = int(parts[4])
            roll_deg   = float(parts[5])
            pitch_deg  = float(parts[6])
            yaw_deg    = float(parts[7])
        except (ValueError, IndexError):
            return

        # ---- normalise flex (0 = flat, 1 = bent) ----
        f_thumb  = self.flex_normalise(thumb_raw,  'thumb')
        f_index  = self.flex_normalise(index_raw,  'index')
        f_middle = self.flex_normalise(middle_raw, 'middle')
        f_ring   = self.flex_normalise(ring_raw,   'ring')
        f_pinky  = self.flex_normalise(pinky_raw,  'pinky')

        # ---- wrist angles (degrees → radians, subtract offset) ----
        DEG2RAD = math.pi / 180.0
        w_yaw   = self.clamp('wrist_yaw',
                             (yaw_deg   - self.yaw_off)   * DEG2RAD)
        w_pitch = self.clamp('wrist_pitch',
                             (pitch_deg - self.pitch_off)  * DEG2RAD)
        w_dev   = self.clamp('wrist_dev',
                             (roll_deg  - self.roll_off)   * DEG2RAD)

        # ---- finger angles ----
        th_j1, th_pip = self.finger_joints(
            f_thumb,
            self.limits['thumb_j1'], self.limits['thumb_pip'])

        ix_j1, ix_pip, ix_dip = self.finger_joints(
            f_index,
            self.limits['index_j1'], self.limits['index_pip'],
            self.limits['index_dip'])

        md_j1, md_pip, md_dip = self.finger_joints(
            f_middle,
            self.limits['middle_j1'], self.limits['middle_pip'],
            self.limits['middle_dip'])

        rn_j1, rn_pip, rn_dip = self.finger_joints(
            f_ring,
            self.limits['ring_j1'], self.limits['ring_pip'],
            self.limits['ring_dip'])

        pk_j1, pk_pip, pk_dip = self.finger_joints(
            f_pinky,
            self.limits['pinky_j1'], self.limits['pinky_pip'],
            self.limits['pinky_dip'])

        # ---- build JointState message ----
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        msg.position = [
            w_yaw, w_pitch, w_dev,
            th_j1, th_pip,
            ix_j1, ix_pip, ix_dip,
            md_j1, md_pip, md_dip,
            rn_j1, rn_pip, rn_dip,
            pk_j1, pk_pip, pk_dip,
        ]
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SerialBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.ser.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
