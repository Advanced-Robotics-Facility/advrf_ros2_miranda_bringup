import atexit
import tempfile
import os
import yaml
from pathlib import Path

from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition
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
        LaunchConfiguration('namespace').perform(context),
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

    namespace = LaunchConfiguration("namespace").perform(context)
    namespace = "/" + namespace.strip("/") if namespace.strip("/") else ""
    moveit_namespace = LaunchConfiguration('moveit_namespace').perform(context)
    moveit_namespace = '/' + moveit_namespace.strip('/') if moveit_namespace.strip('/') else namespace + '/moveit'
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
    feedback_topic = transport_namespace.rstrip('/') + '/rx/joint_states'
    feedback_remappings = [('joint_states', feedback_topic), ('/joint_states', feedback_topic)]
    # Some MoveIt components use absolute names. Keep those inside the same scope.
    interfaces = (
        'planning_scene', 'monitored_planning_scene', 'planning_scene_world',
        'collision_object', 'attached_collision_object', 'display_planned_path',
        'display_contacts', 'trajectory_execution_event', 'move_action',
        'execute_trajectory', 'get_planning_scene', 'apply_planning_scene',
        'compute_ik', 'compute_fk', 'plan_kinematic_path', 'check_state_validity',
        'query_planner_interface', 'get_planner_params', 'set_planner_params',
        'clear_octomap', 'get_group_urdf', 'recognize_objects',
    )
    moveit_remappings = feedback_remappings + [
        ('/' + name, moveit_namespace + '/' + name) for name in interfaces
    ] + [('tf', '/tf'), ('tf_static', '/tf_static')]

    # RViz stores the MoveGroup namespace in its display config, not a ROS parameter.
    # Adapt a private copy so custom robot namespaces work without editing the source.
    rviz_document = yaml.safe_load(rviz_config.read_text())
    for display in rviz_document.get('Visualization Manager', {}).get('Displays', []):
        if display.get('Class') == 'rviz_default_plugins/MarkerArray' and display.get('Name') == 'Selected Joint':
            display['Topic']['Value'] = namespace + '/inputs/selected_joint_marker'
        if display.get('Class') == 'moveit_rviz_plugin/MotionPlanning':
            display['Move Group Namespace'] = moveit_namespace
            display['Planning Scene Topic'] = moveit_namespace + '/monitored_planning_scene'
            display.setdefault('Planned Path', {})['Trajectory Topic'] = moveit_namespace + '/display_planned_path'
    rviz_directory = tempfile.TemporaryDirectory(prefix='advrf-moveit-rviz-')
    atexit.register(rviz_directory.cleanup)
    adapted_rviz = Path(rviz_directory.name) / 'moveit.rviz'
    adapted_rviz.write_text(yaml.safe_dump(rviz_document))

    # Prefer the libraries shipped with this ROS installation over /usr/local.
    ros_lib = str(Path(get_package_prefix('moveit_ros_move_group')) / 'lib')
    moveit_environment = {'LD_LIBRARY_PATH': ros_lib + os.pathsep + os.environ.get('LD_LIBRARY_PATH', '')}
    actions = [
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            namespace=moveit_namespace,
            remappings=[("tf", "/tf"), ("tf_static", "/tf_static")],
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
            namespace=moveit_namespace,
            output="screen",
            parameters=[moveit_config.robot_description],
            remappings=moveit_remappings,
        ),
        Node(
            package="moveit_ros_move_group",
            executable="move_group",
            namespace=moveit_namespace,
            additional_env=moveit_environment,
            output="screen",
            parameters=[moveit_config.to_dict()],
            remappings=moveit_remappings,
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            namespace=moveit_namespace,
            name="moveit_rviz",
            additional_env={**moveit_environment, "LC_ALL": "C.UTF-8"},
            output="screen",
            arguments=["-d", str(adapted_rviz)],
            parameters=[
                moveit_config.robot_description,
                moveit_config.robot_description_semantic,
                moveit_config.planning_pipelines,
                moveit_config.robot_description_kinematics,
                moveit_config.joint_limits,
            ],
            remappings=moveit_remappings,
        ),
    ]

    actions.append(Node(
        package='advrf_ros2_io', executable='selected_joint_marker_node',
        namespace=namespace, output='screen',
        parameters=[{'robot_description': robot['description']}],
    ))
    controllers = Path(get_package_share_directory('advrf_ros2_bringup')) / 'launch/controllers.launch.py'
    return actions + [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(controllers)),
        launch_arguments={
            'config_dir': config_dir, 'namespace': namespace,
            'ecat_namespace': transport_namespace,
            'robot_description_file': str(description_file),
            'control_mode': LaunchConfiguration('control_mode').perform(context),
        }.items()), IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(controllers.with_name('hardware.launch.py'))),
            condition=IfCondition(LaunchConfiguration('start_bridge')),
            launch_arguments={'config_dir': config_dir, 'namespace': namespace,
                              'ecat_namespace': transport_namespace,
                              'active_tx_on_first_msg': LaunchConfiguration('active_tx_on_first_msg').perform(context)}.items())]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("config_dir", default_value=get_package_share_directory("advrf_ros2_miranda_bringup")),
            DeclareLaunchArgument('moveit_namespace', default_value='',
                                  description='Default: <namespace>/moveit'),
            DeclareLaunchArgument('active_tx_on_first_msg', default_value='', choices=['', 'true', 'false']),
            DeclareLaunchArgument("ecat_namespace", default_value=""),
            DeclareLaunchArgument(
                "start_bridge", default_value="false",
                description="Start the EtherCAT bridge locally",
            ),
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
                "namespace",
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
