"""
Launch file for MARS hand project.

Starts:
  1. robot_state_publisher  -- reads URDF, publishes /tf
  2. serial_bridge          -- reads Arduino serial, publishes /joint_states
     OR joint_state_publisher_gui  (when gui:=true, for testing without hardware)
  3. rviz2                  -- visualisation

Usage:
  ros2 launch mars_hand display.launch.py
  ros2 launch mars_hand display.launch.py port:=/dev/ttyUSB0
  ros2 launch mars_hand display.launch.py gui:=true
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_dir = get_package_share_directory('mars_hand')
    urdf_file = os.path.join(pkg_dir, 'urdf', 'hand.urdf')
    rviz_file = os.path.join(pkg_dir, 'rviz', 'config.rviz')

    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    gui = LaunchConfiguration('gui')

    return LaunchDescription([
        # ---- arguments ----
        DeclareLaunchArgument('port', default_value='/dev/ttyACM0',
                              description='Arduino serial port'),
        DeclareLaunchArgument('baud', default_value='115200',
                              description='Serial baud rate'),
        DeclareLaunchArgument('gui', default_value='false',
                              description='Launch joint_state_publisher_gui instead of serial_bridge'),

        # ---- robot_state_publisher (URDF -> /tf) ----
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_desc}],
        ),

        # ---- serial_bridge (Arduino -> /joint_states) ----
        # only runs when gui:=false (the default)
        Node(
            package='mars_hand',
            executable='serial_bridge',
            parameters=[{
                'port': LaunchConfiguration('port'),
                'baud': 115200,
            }],
            condition=UnlessCondition(gui),
        ),

        # ---- joint_state_publisher_gui (for testing without hardware) ----
        # only runs when gui:=true
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            condition=IfCondition(gui),
        ),

        # ---- RViz ----
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_file],
        ),
    ])
