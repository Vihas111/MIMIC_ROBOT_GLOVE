from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import os

def generate_launch_description():

    urdf_path = os.path.join(
        os.getenv('HOME'),
        'Downloads/proj/ros2_ws/src/mars_hand/urdf/hand.urdf'
    )

    with open(urdf_path, 'r') as f:
        robot_desc = f.read()

    return LaunchDescription([

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': ParameterValue(robot_desc, value_type=str),
                'use_sim_time': False
            }]
        ),

        Node(
            package='mars_hand',
            executable='serial_bridge',
            name='serial_bridge',
            output='screen',
            parameters=[
                {'port': '/dev/ttyACM0'},
                {'thumb_flat': 259}, {'thumb_bent': 130},
                {'index_flat': 100}, {'index_bent': 30},
                {'middle_flat': 195}, {'middle_bent': 40},
                {'ring_flat': 180}, {'ring_bent': 40},
                {'pinky_flat': 247}, {'pinky_bent': 90},
            ]
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen'
        )
    ])
