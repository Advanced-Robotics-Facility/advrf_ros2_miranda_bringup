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
        DeclareLaunchArgument('config_dir', default_value=get_package_share_directory('advrf_ros2_miranda_bringup')),
        DeclareLaunchArgument('active_on_first_msg', default_value='', choices=['', 'true', 'false']),
        DeclareLaunchArgument('namespace', default_value='/advrf/miranda'),
        DeclareLaunchArgument('ecat_namespace', default_value='/advrf/miranda/ecat'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(common)),
            launch_arguments={name: LaunchConfiguration(name) for name in
                              ('config_dir', 'namespace', 'ecat_namespace', 'active_on_first_msg')}.items()),
    ])
