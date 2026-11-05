"""Launch the operator panel, with optional bridge and joystick control."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

ROOT = Path(get_package_share_directory('advrf_ros2_miranda_bringup'))


def setup(context):
    def value(name):
        return LaunchConfiguration(name).perform(context)
    package = 'advrf_ros2_motors_controller'
    filename = 'robot.launch.py'
    args = {name: value(name) for name in
            ('config_dir', 'ecat_namespace', 'control_mode', 'use_joy',
             'robot_description_file', 'start_bridge')}
    args.update(namespace=value('namespace'), use_panel='true', use_rviz='true')
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(
        Path(get_package_share_directory(package)) / 'launch' / filename)),
        launch_arguments=args.items())]


def generate_launch_description():
    defaults = {
        'config_dir': str(ROOT), 'namespace': '/advrf/miranda',
        'ecat_namespace': '', 'control_mode': '', 'use_joy': 'false',
        'robot_description_file': 'auto', 'start_bridge': 'false',
    }
    return LaunchDescription([DeclareLaunchArgument(k, default_value=v) for k, v in defaults.items()]
                             + [OpaqueFunction(function=setup)])
