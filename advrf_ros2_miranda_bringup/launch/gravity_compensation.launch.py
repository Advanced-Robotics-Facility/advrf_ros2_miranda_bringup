from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


ARM_JOINTS = 'yaw_1,pitch_1,yaw_2,pitch_2,yaw_3,pitch_3'


def generate_launch_description():
    share = get_package_share_directory('advrf_ros2_miranda_bringup')
    common = Path(get_package_share_directory('advrf_ros2_bringup')) / 'launch'
    gravity_file = Path(get_package_share_directory(
        'advrf_ros2_gravity_compensation')) / 'launch/gravity_compensation.launch.py'

    arguments = [
        DeclareLaunchArgument('config_dir', default_value=share),
        DeclareLaunchArgument('namespace', default_value='/advrf/miranda'),
        DeclareLaunchArgument('ecat_namespace', default_value=''),
        DeclareLaunchArgument('robot_description_file', default_value='auto'),
        DeclareLaunchArgument('gain_ramp_duration', default_value='3.0'),
        DeclareLaunchArgument('start_bridge', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('active_tx_on_first_msg', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('use_rviz', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('rviz_config', default_value=str(Path(share) / 'rviz/view_robot.rviz')),
    ]

    bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(common / 'hardware.launch.py')),
        condition=IfCondition(LaunchConfiguration('start_bridge')),
        launch_arguments={
            'config_dir': LaunchConfiguration('config_dir'),
            'namespace': LaunchConfiguration('namespace'),
            'ecat_namespace': LaunchConfiguration('ecat_namespace'),
            'active_tx_on_first_msg': LaunchConfiguration('active_tx_on_first_msg'),
        }.items(),
    )
    view = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(common / 'visualization.launch.py')),
        launch_arguments={
            'config_dir': LaunchConfiguration('config_dir'),
            'namespace': LaunchConfiguration('namespace'),
            'ecat_namespace': LaunchConfiguration('ecat_namespace'),
            'robot_description_file': LaunchConfiguration('robot_description_file'),
            'control_mode': 'impedance',
            'use_rviz': LaunchConfiguration('use_rviz'),
            'rviz_config': LaunchConfiguration('rviz_config'),
        }.items(),
    )
    gravity = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(gravity_file)),
        launch_arguments={
            'config_dir': LaunchConfiguration('config_dir'),
            'namespace': LaunchConfiguration('namespace'),
            'ecat_namespace': LaunchConfiguration('ecat_namespace'),
            'robot_description_file': LaunchConfiguration('robot_description_file'),
            'gravity_joints': ARM_JOINTS,
            'gain_ramp_duration': LaunchConfiguration('gain_ramp_duration'),
        }.items(),
    )
    return LaunchDescription(arguments + [bridge, view, gravity])
