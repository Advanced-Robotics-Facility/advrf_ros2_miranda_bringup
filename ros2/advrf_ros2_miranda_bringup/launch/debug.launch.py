"""Launch this robot using its adjacent ROS configuration."""
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
    moveit = value('use_moveit').lower() == 'true'
    package = 'advrf_ros2_miranda_bringup' if moveit else 'advrf_ros2_motors_controller'
    filename = 'moveit.launch.py' if moveit else 'robot.launch.py'
    args = {name: value(name) for name in
            ('config_dir', 'ecat_namespace', 'control_mode', 'use_panel',
             'use_rviz', 'start_bridge', 'use_joy', 'robot_description_file')}
    args['advrf_namespace' if moveit else 'namespace'] = value('namespace')
    if moveit:
        args['use_advrf'] = value('use_advrf')
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(
        Path(get_package_share_directory(package)) / 'launch' / filename)),
        launch_arguments=args.items())]


def generate_launch_description():
    defaults = {
        'config_dir': str(ROOT), 'namespace': '/advrf/miranda',
        'ecat_namespace': '', 'control_mode': '', 'use_panel': 'true',
        'use_rviz': 'false', 'start_bridge': 'false', 'use_joy': 'false',
        'use_moveit': 'false', 'use_advrf': 'true',
        'robot_description_file': 'auto',
    }
    return LaunchDescription([DeclareLaunchArgument(k, default_value=v) for k, v in defaults.items()]
                             + [OpaqueFunction(function=setup)])
