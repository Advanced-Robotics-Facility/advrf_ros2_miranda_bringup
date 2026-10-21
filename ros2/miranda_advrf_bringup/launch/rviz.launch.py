import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _environment_default(name: str) -> str:
    return os.environ.get(name, "")


def _required_file(context, argument: str) -> Path:
    value = LaunchConfiguration(argument).perform(context)
    path = Path(value).expanduser()
    if not value or not path.is_file():
        raise RuntimeError(
            f"{argument} does not name an existing file: '{value}'. "
            "Source the selected ecat-miranda-config/setup.sh first or pass "
            f"{argument}:=<path>."
        )
    return path.resolve()


def _launch_setup(context):
    description_file = _required_file(context, "robot_description_file")
    rviz_config = _required_file(context, "rviz_config")

    robot_description = ParameterValue(
        Command([FindExecutable(name="xacro"), " ", str(description_file)]),
        value_type=str,
    )

    return [
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_description}],
            remappings=[("/joint_states", "/advrf/miranda/rx/joint_states")],
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="screen",
            arguments=["-d", str(rviz_config)],
        ),
    ]


def generate_launch_description():
    package_share = Path(get_package_share_directory("miranda_advrf_bringup"))

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "robot_description_file",
                default_value=_environment_default("ROBOT_DESCRIPTION"),
                description="Miranda URDF or Xacro exported by ecat-miranda-config.",
            ),
            DeclareLaunchArgument(
                "rviz_config",
                default_value=str(package_share / "rviz" / "view_robot.rviz"),
                description="RViz configuration file.",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
