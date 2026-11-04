import tempfile
import yaml
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from advrf_ros2_motors_controller.launch_config import resolve_ecat_namespace
from moveit_configs_utils import MoveItConfigsBuilder


def _required_file(context, argument: str) -> Path:
    value = LaunchConfiguration(argument).perform(context)
    path = Path(value).expanduser()
    if not value or not path.is_file():
        raise RuntimeError(
            f"{argument} does not name an existing file: '{value}'. "
            f"Pass {argument}:=<path> or fix the bringup configuration."
        )
    return path.resolve()


def _launch_setup(context):
    config_dir = LaunchConfiguration("config_dir").perform(context)
    root = Path(config_dir).expanduser().resolve(strict=True)
    if not (root / 'config/robot_config.yaml').is_file():
        raise RuntimeError(f"Missing central ROS configuration: {root / 'config/robot_config.yaml'}")
    defaults = {
        'robot_description_file': root / 'urdf/miranda.urdf.xacro',
        'robot_srdf_file': root / 'srdf/miranda.srdf',
        'kinematics_file': root / 'config/kinematics.yaml',
        'moveit_controllers_file': root / 'config/moveit_controllers.yaml',
        'pilz_cartesian_limits_file': root / 'config/pilz_cartesian_limits.yaml',
        'rviz_config': root / 'rviz/moveit.rviz',
    }
    for name, path in defaults.items():
        if not LaunchConfiguration(name).perform(context) or (
                name == 'robot_description_file' and
                LaunchConfiguration(name).perform(context) == 'auto'):
            context.launch_configurations[name] = str(path)
    from advrf_ros2_motors_controller.robot_config import load_robot
    robot = load_robot(
        config_dir,
        LaunchConfiguration('advrf_namespace').perform(context),
        LaunchConfiguration('robot_description_file').perform(context),
        LaunchConfiguration('control_mode').perform(context),
    )
    expected_controllers_file = (root / 'config/moveit_controllers.yaml').resolve()
    if Path(LaunchConfiguration('moveit_controllers_file').perform(context)).resolve() != expected_controllers_file:
        raise ValueError('Select controllers only in config/moveit_controllers.yaml')
    description_file = _required_file(context, "robot_description_file")
    srdf_file = _required_file(context, "robot_srdf_file")
    kinematics_file = _required_file(context, "kinematics_file")
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
    # MoveItConfigsBuilder reads its standard YAML once; this temporary adapter
    # is derived from config/robot_config.yaml and is never edited.
    with tempfile.TemporaryDirectory(prefix='advrf-moveit-') as directory:
        path = Path(directory) / 'joint_limits.yaml'
        path.write_text(yaml.safe_dump(robot['moveit_limits']))
        builder.joint_limits(file_path=str(path))
    moveit_config = builder.to_moveit_configs()

    namespace = LaunchConfiguration("advrf_namespace").perform(context)
    namespace = "/" + namespace.strip("/") if namespace.strip("/") else ""
    joint_parameters = robot['limits']
    joints = joint_parameters.get("joints", [])
    if not joints:
        raise RuntimeError("Central robot configuration has no controlled joints")

    action_name = robot['action_name']
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
    if not LaunchConfiguration('ecat_namespace').perform(context):
        context.launch_configurations['ecat_namespace'] = namespace.rstrip('/') + '/ecat'
    transport_namespace = resolve_ecat_namespace(
        LaunchConfiguration("ecat_namespace").perform(context), "", namespace)
    feedback_remappings = [
        ("/joint_states", transport_namespace.rstrip("/") + "/rx/joint_states")
    ]

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
        ),
    ]

    from advrf_ros2_motors_controller.robot_launch import stack_nodes
    return actions + stack_nodes(
        robot, namespace, transport_namespace, panel=False, bridge=True, joy=False
    )


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("config_dir", default_value=get_package_share_directory("advrf_ros2_miranda_bringup")),
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
                "moveit_controllers_file",
                default_value="",
            ),
            DeclareLaunchArgument(
                "pilz_cartesian_limits_file",
                default_value="",
            ),
            DeclareLaunchArgument(
                "rviz_config",
                default_value="",
            ),
            DeclareLaunchArgument(
                "advrf_namespace",
                default_value="/advrf/miranda",
                description="High-level ROS namespace",
            ),
            DeclareLaunchArgument(
                "control_mode",
                default_value="",
                choices=["", "position", "impedance", "velocity", "torque", "current"],
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
