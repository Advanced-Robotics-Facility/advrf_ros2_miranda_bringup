# Miranda ADVRF ROS 2 bringup

This repository owns Miranda's ROS configuration, robot model, MoveIt setup and
launch files. The native ROS package is in `ros2/advrf_ros2_miranda_bringup`;
mesh dependency submodules remain under `dependencies/`.

```bash
git submodule update --init --recursive
source /opt/ros/jazzy/setup.bash
colcon build --packages-up-to advrf_ros2_miranda_bringup
source install/setup.bash

# Controllers and debug panel
ros2 launch advrf_ros2_miranda_bringup debug.launch.py

# Add joystick
ros2 launch advrf_ros2_miranda_bringup debug.launch.py use_joy:=true

# MoveIt with real ADVRF controls
ros2 launch advrf_ros2_miranda_bringup miranda.launch.py use_moveit:=true use_rviz:=true

# MoveIt with mock ros2_control
ros2 launch advrf_ros2_miranda_bringup miranda.launch.py \
  use_moveit:=true use_advrf:=false use_rviz:=true
```

The installed package share contains `config/`, `urdf/`, `srdf/`, `rviz/` and
`launch/`. Configuration is selected through ROS package discovery, with an
optional `config_dir` override. No EC_CFG discovery is needed for ROS settings.
See the [package README](ros2/advrf_ros2_miranda_bringup/README.md) for file roles
and launch options.

The separate ecat-miranda-config repository retains EtherCAT master/client
configuration, device ID maps, client motor profiles and firmware. Its profile
helpers locate this installed ROS package. Starting the optional native bridge
still requires the client environment. The native bridge lacks replCmd, so the
motor-power services require a compatible backend.

Bench has a separate `advrf_ros2_bench_bringup` package with its own configuration
and `debug.launch.py` / `bench.launch.py`; it does not require a URDF or MoveIt.
