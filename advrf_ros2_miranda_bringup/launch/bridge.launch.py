"""Miranda paths for the shared hardware launch."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    common = Path(get_package_share_directory('advrf_ros2_bringup')) / 'launch/hardware.launch.py'
    return LaunchDescription([
        DeclareLaunchArgument('bridge_config', default_value=str(Path(
            get_package_share_directory('advrf_ros2_miranda_bringup')) / 'config/advrf_bridge.yaml')),
        DeclareLaunchArgument('active_tx_on_first_msg', default_value='', choices=['', 'true', 'false']),
        DeclareLaunchArgument('namespace', default_value='/advrf/miranda'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(common)),
            launch_arguments={name: LaunchConfiguration(name) for name in
                              ('bridge_config', 'namespace', 'active_tx_on_first_msg')}.items()),
    ])
