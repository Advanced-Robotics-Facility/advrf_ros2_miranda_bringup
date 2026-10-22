# Miranda ADVRF bringup

This repository collects the ROS 2 bringup package and its mesh dependencies for
Miranda. Robot-specific EtherCAT, URDF, SRDF, MoveIt, controller, and RViz
configuration remains in the separate
[`ecat-miranda-config`](https://github.com/Advanced-Robotics-Facility/ecat-miranda-config)
repository.

## Repository layout

```text
miranda_advrf_bringup/
├── dependencies/
│   ├── concert_resources/       # Git submodule, ROS 2 branch
│   └── iit-dagana-ros-pkg/      # Git submodule, ROS 2 branch
└── ros2/
    └── miranda_advrf_bringup/   # ROS 2 bringup package
```

## Clone and build

Clone the repository into a ROS 2 workspace together with its submodules:

```bash
cd ~/ros2_ws/src
git clone --recurse-submodules \
  https://github.com/Advanced-Robotics-Facility/miranda_advrf_bringup.git

cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-up-to miranda_advrf_bringup
source install/setup.bash
```

For an existing checkout, initialize or update the dependencies with:

```bash
git submodule update --init --recursive
```

## Select the robot configuration

Use `ecat-miranda-config` and source before launching:

```bash
source /path/to/ecat-miranda-config/setup.sh
```

The setup script exports `ADVRF_CONFIG_ROOT`, `ROBOT_DESCRIPTION`, `ROBOT_SRDF`,
`ROS2_CONTROLLERS`, and `MOVEIT_CONTROLLERS`. The bringup reads those paths at
launch time.

## Launch

Visualize the robot state published by ADVRF:

```bash
ros2 launch miranda_advrf_bringup rviz.launch.py
```

Start MoveIt and RViz using the selected Miranda configuration:

```bash
ros2 launch miranda_advrf_bringup moveit.launch.py
```

By default, the MoveIt launch starts the standard ROS 2 control demo stack configured by
Miranda's `miranda.ros2_control.xacro` and `ros2_controllers.yaml`: the mock
`GenericSystem`, `joint_state_broadcaster`, `arm_controller`, and
`gripper_controller`. It publishes the standard `/joint_states` topic and does
not use an ADVRF-specific joint-state topic.

For the real robot, start the EtherCAT master and middleware first, stop any
standalone ADVRF motor-controller launches, then run:

```bash
ros2 launch miranda_advrf_bringup moveit.launch.py \
  use_advrf:=true
```

This mode remaps robot-state publishing to ADVRF feedback, configures MoveIt to
use `/advrf/miranda/advrf_motors_controller/follow_joint_trajectory`, and starts
exactly one shared joint converter, trajectory/GoTo controller, motor-power
service, and operator panel. It does not start mock `ros2_control`, and motors
remain stopped until START is requested. Set `use_panel:=false` to omit the
panel. The middleware joint-state names must match the URDF, including
`dagana_A_claw_joint`. The namespace, joint set, motor map/profile and action
name are resolved from `EC_CFG` and its ROS 2 configuration; launch arguments
are optional overrides.
