import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node
from advrf_ros2_motors_controller.launch_config import optional_config, RobotNamespace
from advrf_ros2_motors_controller.panel_config import load_parameters
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


def _launch_setup(context):
    use_advrf = LaunchConfiguration("use_advrf").perform(context).lower() == "true"
    description_file = _required_file(context, "robot_description_file")
    srdf_file = _required_file(context, "robot_srdf_file")
    kinematics_file = _required_file(context, "kinematics_file")
    joint_limits_file = _required_file(context, "joint_limits_file")
    controllers_file = _required_file(context, "moveit_controllers_file")
    cartesian_limits_file = _required_file(context, "pilz_cartesian_limits_file")
    rviz_config = _required_file(context, "rviz_config")

    builder = (
        MoveItConfigsBuilder(
            "miranda", package_name="advrf_ros2_miranda_bringup"
        )
        .robot_description(file_path=str(description_file))
        .robot_description_semantic(file_path=str(srdf_file))
        .robot_description_kinematics(file_path=str(kinematics_file))
        .joint_limits(file_path=str(joint_limits_file))
        .planning_pipelines()
        .planning_scene_monitor(
            publish_robot_description=True,
            publish_robot_description_semantic=True,
        )
        .pilz_cartesian_limits(file_path=str(cartesian_limits_file))
        .trajectory_execution(
            file_path=str(controllers_file), moveit_manage_controllers=False
        )
    )
    moveit_config = builder.to_moveit_configs()

    namespace = LaunchConfiguration("advrf_namespace").perform(context)
    namespace = "/" + namespace.strip("/") if namespace.strip("/") else ""
    trajectory_config = optional_config(
        LaunchConfiguration("trajectory_config").perform(context),
        str(joint_limits_file),
        "trajectory_config",
    )
    if use_advrf:
        joint_parameters = load_parameters(str(joint_limits_file), namespace)
        joints = joint_parameters.get("joints", [])
        if not joints:
            raise RuntimeError(f"No controlled joints in {joint_limits_file}")

        trajectory_parameters = (
            load_parameters(trajectory_config, namespace) if trajectory_config else {}
        )
        action_name = trajectory_parameters.get(
            "action_name", "advrf_motors_controller/follow_joint_trajectory"
        )
        if not isinstance(action_name, str) or "/" not in action_name.strip("/"):
            raise RuntimeError(
                "trajectory action_name must contain a controller and action namespace"
            )
        full_action_name = (
            action_name
            if action_name.startswith("/")
            else f"{namespace}/{action_name}" if namespace else f"/{action_name}"
        )
        controller_name, action_namespace = full_action_name.rsplit("/", 1)
        moveit_config.trajectory_execution = {
            "moveit_manage_controllers": False,
            "moveit_controller_manager": (
                "moveit_simple_controller_manager/MoveItSimpleControllerManager"
            ),
            "trajectory_execution": {
                "allowed_execution_duration_scaling": 1.2,
                "allowed_goal_duration_margin": 0.5,
                "allowed_start_tolerance": 0.01,
                "execution_duration_monitoring": True,
            },
            "moveit_simple_controller_manager": {
                "controller_names": [controller_name],
                controller_name: {
                    "type": "FollowJointTrajectory",
                    "action_ns": action_namespace,
                    "default": True,
                    "joints": joints,
                },
            },
        }
    feedback_remappings = (
        [("/joint_states", f"{namespace}/rx/joint_states")]
        if use_advrf
        else []
    )

    actions = [
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
            remappings=feedback_remappings,
        ),
        Node(
            package="moveit_ros_move_group",
            executable="move_group",
            output="screen",
            parameters=[moveit_config.to_dict()],
            remappings=feedback_remappings,
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
            remappings=feedback_remappings,
            condition=IfCondition(LaunchConfiguration("use_rviz")),
        ),
    ]

    if not use_advrf:
        ros2_controllers_file = _required_file(context, "ros2_controllers_file")
        actions[2:2] = [
            Node(
                package="controller_manager",
                executable="ros2_control_node",
                output="screen",
                parameters=[str(ros2_controllers_file)],
                remappings=[
                    ("/controller_manager/robot_description", "/robot_description"),
                ],
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                output="screen",
                arguments=["joint_state_broadcaster"],
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                output="screen",
                arguments=["arm_controller"],
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                output="screen",
                arguments=["gripper_controller"],
            ),
        ]
        return actions

    launch_dir = Path(
        get_package_share_directory("advrf_ros2_motors_controller")
    ) / "launch"
    shared = {
        "ec_cfg": LaunchConfiguration("ec_cfg").perform(context),
        "ros2_cfg": LaunchConfiguration("ros2_cfg").perform(context),
        "namespace": namespace or "/",
        "joint_limits": str(joint_limits_file),
        "robot_id_map": LaunchConfiguration("robot_id_map").perform(context),
        "control_mode": LaunchConfiguration("control_mode").perform(context),
        "motor_profile": LaunchConfiguration("motor_profile").perform(context),
        "motor_profiles_dir": LaunchConfiguration("motor_profiles_dir").perform(context),
    }

    def include(filename, arguments, condition=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(launch_dir / filename)),
            launch_arguments=arguments.items(),
            condition=condition,
        )

    actions.extend(
        [
            include(
                "go_to.launch.py",
                {
                    **shared,
                    "trajectory_config": trajectory_config or "",
                    "command_enabled": "true",
                },
            ),
            include(
                "motors.launch.py",
                {
                    **shared,
                    "start_gains": LaunchConfiguration("start_gains").perform(context),
                    "auto_start_motors": "false",
                },
            ),
            include(
                "panel.launch.py",
                {
                    "ec_cfg": shared["ec_cfg"],
                    "ros2_cfg": shared["ros2_cfg"],
                    "namespace": shared["namespace"],
                    "joint_limits": shared["joint_limits"],
                },
                IfCondition(LaunchConfiguration("use_panel")),
            ),
        ]
    )
    return actions


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
                "ros2_controllers_file",
                default_value=_environment_or_config(
                    "ROS2_CONTROLLERS",
                    "ros2/config/ros2_controllers.yaml",
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
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument("use_panel", default_value="true"),
            DeclareLaunchArgument(
                "use_advrf",
                default_value="false",
                description="Use real ADVRF feedback and motor controllers instead of mock ros2_control",
            ),
            DeclareLaunchArgument(
                "advrf_namespace",
                default_value=RobotNamespace(),
                description="Defaults to EC_CFG ros2.namespace",
            ),
            DeclareLaunchArgument(
                "ec_cfg",
                default_value=EnvironmentVariable("EC_CFG", default_value=""),
            ),
            DeclareLaunchArgument(
                "ros2_cfg",
                default_value=EnvironmentVariable("ROS2_CFG", default_value=""),
            ),
            DeclareLaunchArgument("robot_id_map", default_value=""),
            DeclareLaunchArgument(
                "control_mode",
                default_value="position",
                choices=["position", "impedance", "velocity", "torque", "current"],
            ),
            DeclareLaunchArgument("motor_profile", default_value=""),
            DeclareLaunchArgument("motor_profiles_dir", default_value=""),
            DeclareLaunchArgument("trajectory_config", default_value=""),
            DeclareLaunchArgument("start_gains", default_value=""),
            OpaqueFunction(function=_launch_setup),
        ]
    )
