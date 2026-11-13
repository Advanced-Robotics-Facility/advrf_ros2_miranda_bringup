# advrf_ros2_miranda_bringup
ros version: jazzy

## Quick Use

ROS and workspace built and sourced. Run commands from the workspace root.

### 1. Dummy — everything on one PC

Local configuration in `configs/ecat-miranda-config/`:

- `robot_ecat/ecat_config.yaml`: `ec_board_ctrl.eth_iface: lo`.
- `ec_cfg.yaml`: `network.protocol: tcp`, `hostname: localhost`, `port: 5000`.
- `robot_ecat/ecat_dummy_cfg.yaml`:

```yaml
device:
  SYNAPTICON_v301: [11, 12, 13, 14, 15, 16, 302]
```

**Terminal 1 — master**

```bash
ecat_ws/install/bin/repl -f configs/ecat-miranda-config/robot_ecat/ecat_config.yaml -d
```

**Terminal 2 — bridge + joystick + controllers + RViz**

```bash
export EC_CFG="$PWD/configs/ecat-miranda-config/ec_cfg.yaml"
ros2 launch advrf_ros2_miranda_bringup miranda.launch.py start_bridge:=true use_joy:=true
```

**Or, instead of Terminal 2 — bridge + controllers + MoveIt + RViz**

```bash
export EC_CFG="$PWD/configs/ecat-miranda-config/ec_cfg.yaml"
ros2 launch advrf_ros2_miranda_bringup moveit.launch.py start_bridge:=true
```

### 2. Robot — master and bridge on robot, bringup on PC

On the robot, set `ec_board_ctrl.eth_iface` to the real EtherCAT interface.
Use `network.protocol: iddp` for IDDP/Xenomai, or `tcp` for non-Xenomai.
Keep `hostname: localhost` and `port: 5000`.

**Robot, Terminal 1 — master**

```bash
ecat_ws/install/bin/repl -f configs/ecat-miranda-config/robot_ecat/ecat_config.yaml
```

**Robot, Terminal 2 — bridge**

```bash
export EC_CFG="$PWD/configs/ecat-miranda-config/ec_cfg.yaml"
ros2 launch advrf_ros2_miranda_bringup bridge.launch.py
```

The EtherCAT client starts devices during bridge initialization.

**PC — joystick + controllers + panel + RViz**

```bash
ros2 launch advrf_ros2_miranda_bringup miranda.launch.py use_joy:=true
```

**Or — controllers + MoveIt + RViz**

```bash
ros2 launch advrf_ros2_miranda_bringup moveit.launch.py
```

Run one PC bringup. `start_bridge` defaults to `false`; no `EC_CFG` needed on PC.

**Check**

```bash
ros2 topic echo /advrf/miranda/ecat/rx/joint_states --once
ros2 topic echo /diagnostics --once
```

**TX activation**

TX starts inactive. With joystick, press **A / Cross** to toggle it.
Without joystick, enable it when ready to send commands:

```bash
ros2 service call /advrf/miranda/ecat/set_active_tx std_srvs/srv/SetBool '{data: true}'
```

Use `data: false` to disable TX. Feedback remains available. The 500 ms watchdog
runs only while active, starting immediately at activation. A timeout deactivates
TX and latches a STOP fault; restart the bridge before reactivation.

To activate automatically on the first valid command:

```bash
ros2 launch advrf_ros2_miranda_bringup bridge.launch.py active_tx_on_first_msg:=true
# Local all-in-one alternative:
ros2 launch advrf_ros2_miranda_bringup moveit.launch.py start_bridge:=true active_tx_on_first_msg:=true
```

Default: `false`. Explicit `set_active_tx(false)` cancels automatic activation;
use the service or A / Cross to reactivate. `read_only` is removed.

## Edit Config

Configuration defaults are installed with `advrf_ros2_miranda_bringup`. Override files with explicit paths.

| Argument | Default resource | Purpose |
| --- | --- | --- |
| `robot_config` | `config/robot_config.yaml` | Motor IDs, gains, limits |
| `controller_config` | `config/moveit_controllers.yaml` | Joint controller mapping |
| `controllers_config` | `config/advrf_controllers.yaml` | Controller node parameters |
| `joint_control_config` | `config/joint_control.yaml` | Manual and joystick control |
| `bridge_config` | `config/advrf_bridge.yaml` | EtherCAT bridge parameters |
| `robot_description_file` | `urdf/miranda.urdf.xacro` | Robot model |
| `robot_srdf_file` | `srdf/miranda.srdf` | MoveIt semantic model |
| `kinematics_file` | `config/kinematics.yaml` | MoveIt kinematics |
| `moveit_controllers_file` | `config/moveit_controllers.yaml` | MoveIt controller mapping |
| `pilz_cartesian_limits_file` | `config/pilz_cartesian_limits.yaml` | Cartesian limits |

- `namespace`: `/advrf/miranda` by default for the robot stack.
- `start_bridge`: `false` by default; enable for an all-in-one launch.
- `EC_CFG`: EtherCAT client configuration on the machine running the bridge.
- `rviz_config`: RViz configuration; default depends on the selected launch.
- `gain_ramp_duration`: gravity compensation gain transition duration, default `3.0` seconds.
- Use `ros2 launch advrf_ros2_miranda_bringup <launch_file> --show-args` for the arguments supported by that launch.

## Nodes Details

This package composes nodes from the shared stack; it defines no custom node executable.

| Launch | Purpose |
| --- | --- |
| `miranda.launch.py` | Controllers, optional joystick/panel, RViz and optional bridge |
| `bridge.launch.py` | EtherCAT bridge on the robot |
| `moveit.launch.py` | MoveIt, controllers, RViz and optional bridge |
| `gravity_compensation.launch.py` | Gravity compensation, optional bridge and RViz |

- Feedback: `/advrf/miranda/ecat/rx/joint_states` (`sensor_msgs/msg/JointState`).
- Motor commands: `/advrf/miranda/ecat/tx/motors` (`advrf_ros2_interfaces/msg/MotorTxPdo`).
- TX activation: `/advrf/miranda/ecat/set_active_tx` (`std_srvs/srv/SetBool`).
- Gravity activation: `/advrf/miranda/set_gravity_compensation` (`std_srvs/srv/SetBool`) when gravity compensation is launched.
- Controller and bridge details: see the `advrf_ros2_motors_controller` and `advrf_ros2_ecat` README files.

## Dependencies

- `ament_index_python`
- `advrf_ros2_bringup`
- `advrf_ros2_gravity_compensation`
- `advrf_ros2_motors_controller`
- `concert_resources`
- `dagana_urdf`
- `launch`
- `launch_ros`
- `moveit_configs_utils`
- `moveit_kinematics`
- `moveit_planners`
- `moveit_ros_move_group`
- `moveit_ros_visualization`
- `moveit_simple_controller_manager`
- `robot_state_publisher`
- `rviz2`
- `advrf_ros2_io`
- `rmw_cyclonedds_cpp`
- `tf2_ros`
- `xacro`

## TroubleShooting

| Symptom | Check |
| --- | --- |
| Missing robot model or YAML | Installed resources and explicit file arguments |
| No feedback | Master/backend, bridge process, `EC_CFG` and namespace |
| No motor commands transmitted | TX activation and selected controller |
| Watchdog STOP fault | Restore command flow and restart the bridge before reactivation |
| MoveIt cannot execute | Controller mapping, joint names, action namespace and feedback |
| Joystick has no effect | `use_joy:=true`, device connection and `joint_control_config` |
