import os
import tempfile
import yaml
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node
from advrf_ros2_motors_controller.launch_config import optional_config, RobotNamespace, ros2_folder, resolve_ecat_namespace
from advrf_ros2_motors_controller.panel_config import load_parameters
from moveit_configs_utils import MoveItConfigsBuilder


def _config_default(relative_path: str) -> str:
    ec_cfg = os.environ.get("EC_CFG", "")
    if not ec_cfg:
        return ""
    return str(ros2_folder(Path(ec_cfg).expanduser().resolve()) / relative_path)


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
    config_dir = LaunchConfiguration("config_dir").perform(context)
    robot = None
    planning_robot = None
    if config_dir:
        root = Path(config_dir).expanduser().resolve(strict=True)
        defaults = {
            'robot_description_file': root / 'urdf/miranda.urdf.xacro',
            'robot_srdf_file': root / 'srdf/miranda.srdf',
            'kinematics_file': root / 'config/kinematics.yaml',
            'joint_limits_file': root / 'config/joint_limits.yaml',
            'moveit_controllers_file': root / ('config/moveit_controllers.yaml' if use_advrf
                                               else 'config/moveit_mock_controllers.yaml'),
            'ros2_controllers_file': root / 'config/ros2_controllers.yaml',
            'pilz_cartesian_limits_file': root / 'config/pilz_cartesian_limits.yaml',
            'rviz_config': root / 'rviz/moveit.rviz',
        }
        for name, path in defaults.items():
            if not LaunchConfiguration(name).perform(context) or (name == 'robot_description_file' and LaunchConfiguration(name).perform(context) == 'auto'):
                context.launch_configurations[name] = str(path)
        if (root / 'config/robot_config.yaml').is_file():
            if LaunchConfiguration('joint_limits_file').perform(context) != str(root / 'config/joint_limits.yaml'):
                raise ValueError('With robot_config.yaml, edit central motor limits instead of joint_limits_file')
            from advrf_ros2_motors_controller.robot_config import load_robot
            planning_robot = load_robot(config_dir,
                LaunchConfiguration('advrf_namespace').perform(context),
                LaunchConfiguration('robot_description_file').perform(context),
                LaunchConfiguration('control_mode').perform(context))
            if use_advrf:
                robot = planning_robot
                if Path(LaunchConfiguration('moveit_controllers_file').perform(context)).resolve() != root / 'config/moveit_controllers.yaml':
                    raise ValueError('With config_dir, select controllers in config/moveit_controllers.yaml')
        elif use_advrf:
            from advrf_ros2_motors_controller.robot_config import load_robot, joint_limits
            robot = load_robot(config_dir,
                LaunchConfiguration('advrf_namespace').perform(context),
                LaunchConfiguration('robot_description_file').perform(context),
                LaunchConfiguration('control_mode').perform(context))
            limits = joint_limits(LaunchConfiguration('joint_limits_file').perform(context),
                                  robot['limits']['joints'], robot['description'])
            robot['limits'] = limits
            for values in robot['nodes'].values():
                values.update(limits)
    else:
        legacy = {
            'robot_description_file': ('ROBOT_DESCRIPTION', 'urdf/miranda.urdf.xacro'),
            'robot_srdf_file': ('ROBOT_SRDF', 'srdf/miranda.srdf'),
            'kinematics_file': ('', 'config/kinematics.yaml'),
            'joint_limits_file': ('', 'config/joint_limits.yaml'),
            'moveit_controllers_file': ('MOVEIT_CONTROLLERS', 'config/moveit_controllers.yaml'),
            'ros2_controllers_file': ('ROS2_CONTROLLERS', 'config/ros2_controllers.yaml'),
            'pilz_cartesian_limits_file': ('', 'config/pilz_cartesian_limits.yaml'),
            'rviz_config': ('', 'rviz/moveit.rviz'),
        }
        for name, (env, relative) in legacy.items():
            if not LaunchConfiguration(name).perform(context):
                context.launch_configurations[name] = _environment_or_config(env, relative)
    description_file = _required_file(context, "robot_description_file")
    srdf_file = _required_file(context, "robot_srdf_file")
    kinematics_file = _required_file(context, "kinematics_file")
    joint_limits_file = None if planning_robot else _required_file(context, "joint_limits_file")
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
    if planning_robot:
        # MoveItConfigsBuilder reads its standard YAML once; this temporary
        # adapter is derived from the central definition and never edited.
        with tempfile.TemporaryDirectory(prefix='advrf-moveit-') as directory:
            path = Path(directory) / 'joint_limits.yaml'
            path.write_text(yaml.safe_dump(planning_robot['moveit_limits']))
            builder.joint_limits(file_path=str(path))
    else:
        builder.joint_limits(file_path=str(joint_limits_file))
    moveit_config = builder.to_moveit_configs()

    namespace = LaunchConfiguration("advrf_namespace").perform(context)
    namespace = "/" + namespace.strip("/") if namespace.strip("/") else ""
    trajectory_config = None if planning_robot else optional_config(
        LaunchConfiguration("trajectory_config").perform(context),
        str(joint_limits_file),
        "trajectory_config",
    )
    if use_advrf:
        joint_parameters = robot['limits'] if robot else load_parameters(str(joint_limits_file), namespace)
        joints = joint_parameters.get("joints", [])
        if not joints:
            raise RuntimeError(f"No controlled joints in {joint_limits_file}")

        trajectory_parameters = (
            load_parameters(trajectory_config, namespace) if trajectory_config else {}
        )
        action_name = robot['action_name'] if robot else trajectory_parameters.get(
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
    if robot and not LaunchConfiguration('ecat_namespace').perform(context):
        context.launch_configurations['ecat_namespace'] = namespace.rstrip('/') + '/ecat'
    transport_namespace = resolve_ecat_namespace(
        LaunchConfiguration("ecat_namespace").perform(context),
        LaunchConfiguration("ec_cfg").perform(context), namespace)
    feedback_remappings = (
        [("/joint_states", transport_namespace.rstrip("/") + "/rx/joint_states")]
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
        if planning_robot:
            actions.append(Node(package='advrf_ros2_motors_controller', executable='robot_config_node',
                namespace=namespace, output='screen', parameters=[{
                    **planning_robot['configuration_parameters'],
                    'configuration_file': planning_robot['configuration_file'],
                    'robot_description': planning_robot['description'],
                }]))
        return actions

    if robot:
        from advrf_ros2_motors_controller.robot_launch import stack_nodes
        return actions + stack_nodes(robot, namespace, transport_namespace,
            LaunchConfiguration('use_panel').perform(context).lower() == 'true',
            LaunchConfiguration('start_bridge').perform(context).lower() == 'true',
            LaunchConfiguration('use_joy').perform(context).lower() == 'true')

    launch_dir = Path(
        get_package_share_directory("advrf_ros2_motors_controller")
    ) / "launch"
    shared = {
        "ec_cfg": LaunchConfiguration("ec_cfg").perform(context),
        "ros2_cfg": LaunchConfiguration("ros2_cfg").perform(context),
        "namespace": namespace or "/",
        "ecat_namespace": transport_namespace,
        "joint_limits": str(joint_limits_file),
        "robot_id_map": LaunchConfiguration("robot_id_map").perform(context),
        "control_mode": LaunchConfiguration("control_mode").perform(context) or "position",
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
                    "ecat_namespace": shared["ecat_namespace"],
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
            DeclareLaunchArgument("config_dir", default_value=get_package_share_directory("advrf_ros2_miranda_bringup")),
            DeclareLaunchArgument("start_bridge", default_value="false"),
            DeclareLaunchArgument("use_joy", default_value="false"),
            DeclareLaunchArgument("ecat_namespace", default_value=""),
            DeclareLaunchArgument(
                "robot_description_file",
                default_value="",
            ),
            DeclareLaunchArgument(
                "robot_srdf_file",
                default_value="",
            ),
            DeclareLaunchArgument(
                "kinematics_file",
                default_value="",
            ),
            DeclareLaunchArgument(
                "joint_limits_file",
                default_value="",
            ),
            DeclareLaunchArgument(
                "moveit_controllers_file",
                default_value=_environment_or_config(
                    "MOVEIT_CONTROLLERS",
                    "config/moveit_controllers.yaml",
                ),
            ),
            DeclareLaunchArgument(
                "ros2_controllers_file",
                default_value=_environment_or_config(
                    "ROS2_CONTROLLERS",
                    "config/ros2_controllers.yaml",
                ),
            ),
            DeclareLaunchArgument(
                "pilz_cartesian_limits_file",
                default_value="",
            ),
            DeclareLaunchArgument(
                "rviz_config",
                default_value="",
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
                default_value="/advrf/miranda",
                description="High-level ROS namespace",
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
                default_value="",
                choices=["", "position", "impedance", "velocity", "torque", "current"],
            ),
            DeclareLaunchArgument("motor_profile", default_value=""),
            DeclareLaunchArgument("motor_profiles_dir", default_value=""),
            DeclareLaunchArgument("trajectory_config", default_value=""),
            DeclareLaunchArgument("start_gains", default_value=""),
            OpaqueFunction(function=_launch_setup),
        ]
    )
