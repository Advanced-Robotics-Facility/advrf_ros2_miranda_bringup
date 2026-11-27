"""Launch the operator panel, with optional bridge and joystick control."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import SetParameter

ROOT = Path(get_package_share_directory('advrf_ros2_miranda_bringup'))


def setup(context):
    def value(name):
        return LaunchConfiguration(name).perform(context)
    package = 'advrf_ros2_bringup'
    filename = 'robot.launch.py'
    args = {name: value(name) for name in
            ('robot_config', 'controller_config', 'controllers_config', 'joint_control_config', 'bridge_config', 'control_mode', 'use_joy',
             'robot_description_file', 'start_bridge', 'active_tx_on_first_msg')}
    args.update(namespace=value('namespace'), use_panel=value('use_panel'),
                use_rviz=value('use_rviz'), rviz_config=value('rviz_config'),
                gazebo_ecat='true' if value('backend') == 'advrf_gazebo' else 'false')
    robot = IncludeLaunchDescription(PythonLaunchDescriptionSource(str(
        Path(get_package_share_directory(package)) / 'launch' / filename)),
        launch_arguments=args.items())
    if value('backend') == 'advrf_gazebo':
        if args['start_bridge'] != 'false':
            raise ValueError('advrf_gazebo requires start_bridge:=false')
        simulation = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(ROOT / 'launch/gazebo.launch.py')),
            launch_arguments={
                'gui': value('gui'),
                'model_file': args['robot_description_file'],
                'gazebo_ecat_namespace': args['namespace'].rstrip('/') + '/ecat',
                'active_tx_on_first_msg': args['active_tx_on_first_msg'] or 'false',
            }.items(),
        )
        return [SetParameter(name='use_sim_time', value=True), simulation, robot]
    return [robot]


def generate_launch_description():
    defaults = {
        'bridge_config': str(ROOT / 'config/advrf_bridge.yaml'),
        'robot_config': str(ROOT / 'config/robot_config.yaml'),
        'controller_config': str(ROOT / 'config/moveit_controllers.yaml'),
        'controllers_config': str(ROOT / 'config/advrf_controllers.yaml'),
        'joint_control_config': str(ROOT / 'config/joint_control.yaml'), 'namespace': '/advrf/miranda',
        'control_mode': '', 'use_joy': 'false',
        'robot_description_file': str(ROOT / 'urdf/miranda.urdf.xacro'), 'start_bridge': 'false',
        'use_panel': 'true', 'use_rviz': 'true', 'active_tx_on_first_msg': '',
        'rviz_config': str(ROOT / 'rviz/miranda.rviz'),
        'gui': 'true',
    }
    return LaunchDescription([DeclareLaunchArgument(k, default_value=v) for k, v in defaults.items()]
                             + [DeclareLaunchArgument('backend', default_value='advrf',
                                                      choices=['advrf', 'advrf_gazebo']),
                                OpaqueFunction(function=setup)])
