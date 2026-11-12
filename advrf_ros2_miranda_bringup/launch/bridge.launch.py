"""Miranda paths for the shared hardware launch."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def setup(context):
    common = Path(get_package_share_directory('advrf_ros2_bringup')) / 'launch/hardware.launch.py'
    arguments = {
        name: LaunchConfiguration(name).perform(context)
        for name in (
            'bridge_config',
            'namespace',
            'active_tx_on_first_msg',
            'control_mode',
            'motor_start_config',
        )
    }
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(common)),
                                    launch_arguments=arguments.items())]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('bridge_config', default_value=str(Path(
            get_package_share_directory('advrf_ros2_miranda_bringup')) / 'config/advrf_bridge.yaml')),
        DeclareLaunchArgument('active_tx_on_first_msg', default_value='', choices=['', 'true', 'false']),
        DeclareLaunchArgument('namespace', default_value='/advrf/miranda'),
        DeclareLaunchArgument('control_mode', default_value='',
                              description='Hardware startup mode from bridge_config motor_start_profiles'),
        DeclareLaunchArgument('motor_start_config', default_value='',
                              description='Explicit motor profile YAML instead of control_mode'),
        OpaqueFunction(function=setup),
    ])
