"""Start only the Miranda EtherCAT ROS bridge on the embedded computer."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    root = Path(get_package_share_directory('advrf_ros2_miranda_bringup'))
    return LaunchDescription([
        DeclareLaunchArgument('ecat_namespace', default_value='/advrf/miranda/ecat'),
        DeclareLaunchArgument('config_dir', default_value=str(root)),
        Node(
            package='advrf_ros2_ecat',
            executable='bridge_ecat_client_node',
            namespace=LaunchConfiguration('ecat_namespace'),
            output='screen',
            parameters=[PathJoinSubstitution([
                LaunchConfiguration('config_dir'), 'config', 'advrf_bridge.yaml',
            ])],
        ),
    ])
