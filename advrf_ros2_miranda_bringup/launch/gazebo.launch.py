from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    gazebo = Path(get_package_share_directory('advrf_ros2_gazebo'))
    miranda = Path(get_package_share_directory('advrf_ros2_miranda_bringup'))
    resources = ':'.join(
        str(Path(get_package_share_directory(package)).parent)
        for package in ('concert_resources', 'dagana_urdf')
    )
    return LaunchDescription([
        DeclareLaunchArgument('use_gz_ros2_control', default_value='true'),
        DeclareLaunchArgument('gui', default_value='true'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(gazebo / 'launch/gazebo.launch.py')),
            launch_arguments={
                'model_file': str(miranda / 'urdf/miranda.urdf.xacro'),
                'robot_name': 'miranda',
                'resource_paths': resources,
                'use_gz_ros2_control': LaunchConfiguration('use_gz_ros2_control'),
                'gui': LaunchConfiguration('gui'),
            }.items(),
        ),
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=[
                'joint_state_broadcaster', 'joint_trajectory_controller',
                '--controller-manager', '/controller_manager',
                '--controller-manager-timeout', '60',
            ],
            condition=IfCondition(LaunchConfiguration('use_gz_ros2_control')),
            output='screen',
        ),
    ])
