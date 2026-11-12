"""Miranda paths for the shared hardware launch."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


PROFILES = {
    'position': 'motor/miranda_pos_3b.yaml',
    'impedance': 'motor/miranda_imp_d4.yaml',
    'idle': 'motor/miranda_idle.yaml',
}


def setup(context):
    common = Path(get_package_share_directory('advrf_ros2_bringup')) / 'launch/hardware.launch.py'
    mode = LaunchConfiguration('motor_start_mode').perform(context)
    profile = LaunchConfiguration('motor_start_config').perform(context)
    if mode and profile:
        raise ValueError('Choose motor_start_mode or motor_start_config, not both')
    arguments = {name: LaunchConfiguration(name).perform(context) for name in
                 ('bridge_config', 'namespace', 'active_tx_on_first_msg')}
    arguments['motor_start_config'] = profile or PROFILES.get(mode, '')
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(common)),
                                    launch_arguments=arguments.items())]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('bridge_config', default_value=str(Path(
            get_package_share_directory('advrf_ros2_miranda_bringup')) / 'config/advrf_bridge.yaml')),
        DeclareLaunchArgument('active_tx_on_first_msg', default_value='', choices=['', 'true', 'false']),
        DeclareLaunchArgument('namespace', default_value='/advrf/miranda'),
        DeclareLaunchArgument('motor_start_mode', default_value='',
                              choices=['', *PROFILES], description='Hardware mode at bridge startup'),
        DeclareLaunchArgument('motor_start_config', default_value='',
                              description='Explicit motor profile YAML instead of motor_start_mode'),
        OpaqueFunction(function=setup),
    ])
