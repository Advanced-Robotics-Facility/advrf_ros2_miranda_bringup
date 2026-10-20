"""Run MoveIt against Miranda state supplied by ADVRF, without fake hardware."""

import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def _config_default(relative_path: str) -> str:
    root = os.environ.get("ADVRF_CONFIG_ROOT", "")
    return str(Path(root) / relative_path) if root else ""


def _environment_or_config(name: str, relative_path: str) -> str:
    return os.environ.get(name, _config_default(relative_path))


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


def _as_bool(context, argument: str) -> bool:
    value = LaunchConfiguration(argument).perform(context).lower()
    if value not in ("true", "false"):
        raise RuntimeError(f"{argument} must be 'true' or 'false', got '{value}'")
    return value == "true"


def _launch_setup(context):
    description_file = _required_file(context, "robot_description_file")
    srdf_file = _required_file(context, "robot_srdf_file")
    kinematics_file = _required_file(context, "kinematics_file")
    joint_limits_file = _required_file(context, "joint_limits_file")
    controllers_file = _required_file(context, "moveit_controllers_file")
    cartesian_limits_file = _required_file(context, "pilz_cartesian_limits_file")
    rviz_config = _required_file(context, "rviz_config")

    moveit_config = (
        MoveItConfigsBuilder(
            "miranda", package_name="miranda_advrf_bringup"
        )
        .robot_description(file_path=str(description_file))
        .robot_description_semantic(file_path=str(srdf_file))
        .robot_description_kinematics(file_path=str(kinematics_file))
        .joint_limits(file_path=str(joint_limits_file))
        .planning_pipelines()
        .trajectory_execution(
            file_path=str(controllers_file), moveit_manage_controllers=False
        )
        .planning_scene_monitor(
            publish_planning_scene=True,
            publish_geometry_updates=True,
            publish_state_updates=True,
            publish_transforms_updates=True,
            publish_robot_description=True,
            publish_robot_description_semantic=True,
        )
        .pilz_cartesian_limits(file_path=str(cartesian_limits_file))
        .to_moveit_configs()
    )

    joint_states_topic = LaunchConfiguration("joint_states_topic").perform(context)
    allow_execution = _as_bool(context, "allow_trajectory_execution")

    return [
        Node(
            package="miranda_advrf_bringup",
            executable="joint_state_relay.py",
            name="miranda_joint_state_relay",
            output="screen",
            parameters=[{"input_topic": joint_states_topic}],
        ),
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="miranda_world_to_base",
            output="screen",
            arguments=[
                "--frame-id",
                "world",
                "--child-frame-id",
                "base_link",
            ],
        ),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            output="screen",
            parameters=[moveit_config.robot_description],
        ),
        Node(
            package="moveit_ros_move_group",
            executable="move_group",
            output="screen",
            parameters=[
                moveit_config.to_dict(),
                {
                    "allow_trajectory_execution": allow_execution,
                    "publish_robot_description": True,
                    "publish_robot_description_semantic": True,
                },
            ],
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="moveit_rviz",
            additional_env={"LC_ALL": "C.UTF-8"},
            output="screen",
            arguments=["-d", str(rviz_config)],
            parameters=[
                moveit_config.planning_pipelines,
                moveit_config.robot_description_kinematics,
                moveit_config.joint_limits,
            ],
            condition=IfCondition(LaunchConfiguration("use_rviz")),
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "robot_description_file",
                default_value=_environment_or_config(
                    "ROBOT_DESCRIPTION", "ros2/urdf/miranda.urdf.xacro"
                ),
            ),
            DeclareLaunchArgument(
                "robot_srdf_file",
                default_value=_environment_or_config(
                    "ROBOT_SRDF", "ros2/srdf/miranda.srdf"
                ),
            ),
            DeclareLaunchArgument(
                "kinematics_file",
                default_value=_config_default("ros2/config/kinematics.yaml"),
            ),
            DeclareLaunchArgument(
                "joint_limits_file",
                default_value=_config_default("ros2/config/joint_limits.yaml"),
            ),
            DeclareLaunchArgument(
                "moveit_controllers_file",
                default_value=_environment_or_config(
                    "MOVEIT_CONTROLLERS",
                    "ros2/config/moveit_controllers.yaml",
                ),
            ),
            DeclareLaunchArgument(
                "pilz_cartesian_limits_file",
                default_value=_config_default(
                    "ros2/config/pilz_cartesian_limits.yaml"
                ),
            ),
            DeclareLaunchArgument(
                "rviz_config",
                default_value=_config_default("ros2/rviz/moveit.rviz"),
            ),
            DeclareLaunchArgument(
                "joint_states_topic",
                default_value="/advrf/miranda/rx/joint_states",
            ),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument(
                "allow_trajectory_execution",
                default_value="false",
                description=(
                    "Enable only when FollowJointTrajectory servers matching the "
                    "ADVRF MoveIt controller configuration are running."
                ),
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
