from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
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
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('model_file', default_value=str(miranda / 'urdf/miranda.urdf.xacro')),
        DeclareLaunchArgument('gazebo_ecat_namespace', default_value='/advrf/miranda/ecat'),
        DeclareLaunchArgument('active_tx_on_first_msg', default_value='false'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(gazebo / 'launch/gazebo.launch.py')),
            launch_arguments={
                'model_file': LaunchConfiguration('model_file'),
                'robot_name': 'miranda',
                'resource_paths': resources,
                'gui': LaunchConfiguration('gui'),
                'gazebo_ecat_namespace': LaunchConfiguration('gazebo_ecat_namespace'),
                'active_tx_on_first_msg': LaunchConfiguration('active_tx_on_first_msg'),
            }.items(),
        ),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
            output='screen',
        ),
    ])
