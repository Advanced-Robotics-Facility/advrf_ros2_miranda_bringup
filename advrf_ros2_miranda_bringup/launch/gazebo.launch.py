from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    gazebo = Path(get_package_share_directory('advrf_ros2_gazebo'))
    miranda = Path(get_package_share_directory('advrf_ros2_miranda_bringup'))
    resources = ':'.join(
        str(Path(get_package_share_directory(package)).parent)
        for package in ('concert_resources', 'dagana_urdf')
    )
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(gazebo / 'launch/gazebo.launch.py')),
            launch_arguments={
                'model_file': str(miranda / 'urdf/miranda.urdf.xacro'),
                'robot_name': 'miranda',
                'resource_paths': resources,
            }.items(),
        ),
    ])
