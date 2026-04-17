import rclpy
from rclpy.node import Node
import serial
from sensor_msgs.msg import JointState


class SerialBridge(Node):
    def __init__(self):
        super().__init__('serial_bridge')

        self.declare_parameter('port', '/dev/ttyACM0')

        # ---- CALIBRATION ----
        self.declare_parameter('thumb_flat', 260)
        self.declare_parameter('thumb_bent', 130)

        self.declare_parameter('index_flat', 260)
        self.declare_parameter('index_bent', 110)

        self.declare_parameter('middle_flat', 265)
        self.declare_parameter('middle_bent', 130)

        self.declare_parameter('ring_flat', 210)
        self.declare_parameter('ring_bent', 80)

        self.declare_parameter('pinky_flat', 245)
        self.declare_parameter('pinky_bent', 110)

        port = self.get_parameter('port').value
        self.ser = serial.Serial(port, 115200, timeout=1)

        self.get_logger().info(f"Opened {port}")

        self.pub = self.create_publisher(JointState, '/joint_states', 10)
        self.timer = self.create_timer(0.02, self.loop)

    def normalize(self, val, flat, bent):
        val = max(min(val, flat), bent)
        ratio = (flat - val) / (flat - bent)
        return max(0.0, min(1.0, ratio))

    def loop(self):
        line = self.ser.readline().decode(errors='ignore').strip()
        if not line:
            return

        parts = line.split(',')
        if len(parts) < 5:
            return

        try:
            thumb = float(parts[0])
            index = float(parts[1])
            middle = float(parts[2])
            ring = float(parts[3])
            pinky = float(parts[4])
        except:
            return

        # Normalize fingers
        i = self.normalize(index,
            self.get_parameter('index_flat').value,
            self.get_parameter('index_bent').value)

        m = self.normalize(middle,
            self.get_parameter('middle_flat').value,
            self.get_parameter('middle_bent').value)

        r = self.normalize(ring,
            self.get_parameter('ring_flat').value,
            self.get_parameter('ring_bent').value)

        p = self.normalize(pinky,
            self.get_parameter('pinky_flat').value,
            self.get_parameter('pinky_bent').value)

        # Thumb (invert)
        t = -self.normalize(thumb,
            self.get_parameter('thumb_flat').value,
            self.get_parameter('thumb_bent').value)

        t = t * 1.5

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()

        # ✅ ALL JOINTS (INCLUDING WRIST)
        msg.name = [
            'wrist_yaw',
            'wrist_pitch',
            'wrist_dev',

            'index_j1','index_pip','index_dip',
            'middle_j1','middle_pip','middle_dip',
            'ring_j1','ring_pip','ring_dip',
            'pinky_j1','pinky_pip','pinky_dip',
            'thumb_j1','thumb_pip'
        ]

        # ✅ SAME COUNT
        msg.position = [
            0.0, 0.0, 0.0,   # wrist (static)

            i, i * 0.8, i * 0.6,
            m, m * 0.8, m * 0.6,
            r, r * 0.8, r * 0.6,
            p, p * 0.8, p * 0.6,
            t, t * 0.7
        ]

        msg.velocity = []
        msg.effort = []

        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SerialBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
