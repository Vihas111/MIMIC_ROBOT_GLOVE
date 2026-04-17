import os
from glob import glob
from setuptools import setup

package_name = 'mars_hand'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
        (os.path.join('share', package_name, 'urdf'),
            glob('urdf/*')),
        (os.path.join('share', package_name, 'rviz'),
            glob('rviz/*')),
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='Kaustubh',
    maintainer_email='kaustubh@todo.com',
    description='MARS Project glove-to-RViz bridge',
    license='MIT',
    entry_points={
        'console_scripts': [
            'serial_bridge = mars_hand.serial_bridge:main',
        ],
    },
)
