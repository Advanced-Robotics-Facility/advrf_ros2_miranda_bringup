# ADVRF Miranda ROS 2 bringup

All Miranda ROS configuration is installed with this package. EtherCAT
client/master configuration remains in configs/ecat-miranda-config.

```bash
source install/setup.bash
ros2 launch advrf_ros2_miranda_bringup bridge.launch.py
ros2 launch advrf_ros2_miranda_bringup debug.launch.py
ros2 launch advrf_ros2_miranda_bringup debug.launch.py use_joy:=true
ros2 launch advrf_ros2_miranda_bringup moveit.launch.py
```

`config_dir` defaults to this package's installed share directory. Override it
with a directory containing config/ and optional urdf/, srdf/, rviz/ folders.
Default namespace: /advrf/miranda; transport namespace: /advrf/miranda/ecat.
ROS_DOMAIN_ID is a ROS environment setting (the workspace setup defaults to 42).

- config/robot_config.yaml: single motor definition, selected control mode,
  integer IDs, operating limits and five named scalar gains per joint/mode.
- config/advrf_controllers.yaml: timing, tolerances and START policy.
- config/advrf_bridge.yaml: ROS bridge startup policy and QoS.
- config/joint_control.yaml: joystick/manual controls.
- config/moveit_controllers.yaml: shared ADVRF action and ordered joint list.
- urdf/, srdf/, rviz/: robot model and visualization assets.

`moveit.launch.py` starts MoveIt, MoveIt RViz and the ADVRF controllers.
`bridge.launch.py` is the embedded-only entry point: it starts one bridge node
under `/advrf/miranda/ecat`, using `config/advrf_bridge.yaml` (currently a 5 ms
period). It inherits `EC_CFG` from the shell and requires the master to be
running, for example via `repl -d`. It starts no controllers, panel or RViz.
Override `ecat_namespace` or `config_dir` when needed.
`debug.launch.py` starts the controllers, panel and standard robot RViz;
`use_joy` defaults to false.
Both launchers default to `start_bridge:=false` for use with a bridge running
on the embedded computer. Pass `start_bridge:=true` to start the bridge locally:

```bash
ros2 launch advrf_ros2_miranda_bringup debug.launch.py start_bridge:=true
ros2 launch advrf_ros2_miranda_bringup moveit.launch.py start_bridge:=true
```
Only existing gain profiles are included; selecting
an absent mode fails. Gains retain their previous profile order; launch handles
the native position/velocity wire permutation. Change control_mode at startup.
The panel reads limits through the controller's ROS parameter service.

Starting a local bridge requires the selected EtherCAT client environment
(`EC_CFG`) and a running master. When the bridge runs separately, those are
required on its computer. The native bridge starts motors on the first valid
command.


## Editing motor parameters

Select `/advrf/miranda/robot_config_node` in rqt_reconfigure. Gains are scalar
parameters such as `motors.JOINT.profiles.position.gain_0`, not a 5×N array.
Operating limits are `motors.JOINT.limits.position_lower`, `position_upper`,
`max_velocity`, `max_acceleration`. The selected `control_mode` also lives here.
IDs and configured gain bounds are read-only at runtime.

Parameter changes are validated against the complete definition and URDF physical
limits when a model exists. They are staged configuration edits, not live motor
or planner updates. Save them explicitly, stop the stack, and restart it:

```bash
ros2 service call /advrf/miranda/robot_config_node/save std_srvs/srv/Trigger '{}'
```

Save writes the node's `configuration_file` (shown as a read-only parameter),
which is normally the installed package config. With a copied installation,
copy saved changes back to the source config before rebuilding; otherwise a
rebuild can overwrite them. Alternatively launch with `config_dir` pointing to
your source/custom configuration directory.

The launch adapter supplies IDs and gain arrays to ADVRF nodes and standard
`robot_description_planning.joint_limits` to MoveIt. Command gains retain the
native wire conversion; START gains retain original profile ordering. Both are
derived from the same scalar profile. The old advrf_hardware.yaml and
joint_limits.yaml files have been removed from these packaged configs.

Optional per-slot bounds can be added within a profile:

```yaml
profiles:
  position:
    gain_0: 0.009
    gain_1: 0.0
    gain_2: 0.0
    gain_3: 0.0
    gain_4: 0.0
    gain_bounds:
      gain_0:
        min: 0.0
        max: 0.02
```

These numbers illustrate the syntax, not validated motor tuning bounds. Existing
profiles have no invented motor-specific bounds; finite float32 storage bounds
are enforced. Native position/velocity profile gain_3 and gain_4 must stay zero
because of the existing wire representation. Limits and all profiles are
validated before any controller is launched.
