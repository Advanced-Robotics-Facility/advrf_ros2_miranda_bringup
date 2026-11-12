from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    share = get_package_share_directory('advrf_ros2_miranda_bringup')
    common = Path(get_package_share_directory('advrf_ros2_bringup')) / 'launch'
    gravity_file = common / 'gravity_compensation.launch.py'

    arguments = [
        DeclareLaunchArgument('robot_config', default_value=str(Path(share) / 'config/robot_config.yaml')),
        DeclareLaunchArgument('controller_config', default_value=str(Path(share) / 'config/moveit_controllers.yaml')),
        DeclareLaunchArgument('controllers_config', default_value=str(Path(share) / 'config/advrf_controllers.yaml')),
        DeclareLaunchArgument('bridge_config', default_value=str(Path(share) / 'config/advrf_bridge.yaml')),
        DeclareLaunchArgument('namespace', default_value='/advrf/miranda'),
        DeclareLaunchArgument('robot_description_file', default_value=str(Path(share) / 'urdf/miranda.urdf.xacro')),
        DeclareLaunchArgument('gravity_config', default_value=str(Path(share) / 'config/gravity_compensation.yaml')),
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
            'bridge_config': LaunchConfiguration('bridge_config'),
            'namespace': LaunchConfiguration('namespace'),
            'active_tx_on_first_msg': LaunchConfiguration('active_tx_on_first_msg'),
        }.items(),
    )
    view = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(common / 'visualization.launch.py')),
        launch_arguments={
            'namespace': LaunchConfiguration('namespace'),
            'robot_description_file': LaunchConfiguration('robot_description_file'),
            'use_rviz': LaunchConfiguration('use_rviz'),
            'rviz_config': LaunchConfiguration('rviz_config'),
        }.items(),
    )
    gravity = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(gravity_file)),
        launch_arguments={
            'robot_config': LaunchConfiguration('robot_config'),
            'controller_config': LaunchConfiguration('controller_config'),
            'controllers_config': LaunchConfiguration('controllers_config'),
            'namespace': LaunchConfiguration('namespace'),
            'robot_description_file': LaunchConfiguration('robot_description_file'),
            'gravity_config': LaunchConfiguration('gravity_config'),
            'gain_ramp_duration': LaunchConfiguration('gain_ramp_duration'),
        }.items(),
    )
    return LaunchDescription(arguments + [bridge, view, gravity])
