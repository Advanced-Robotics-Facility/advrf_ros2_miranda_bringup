# Miranda — quick start

ROS and workspace built and sourced. Run commands from the workspace root.

## 1. Dummy — everything on one PC

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

## 2. Robot — master and bridge on robot, bringup on PC

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
