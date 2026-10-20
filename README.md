# Miranda ADVRF bringup

This package launches RViz and MoveIt directly from the ROS 2 resources exported
by the active `ecat-miranda-config`. It does not contain copies of Miranda's URDF,
SRDF, kinematics, limits, or controller configuration.

Before launching, select the Miranda configuration:

```bash
source /path/to/ecat-miranda-config/setup.sh
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

Visualize the physical joint feedback:

```bash
ros2 launch miranda_advrf_bringup rviz.launch.py
```

Run MoveIt planning against the physical joint feedback:

```bash
ros2 launch miranda_advrf_bringup moveit.launch.py
```

Both launch files relay `/advrf/miranda/rx/joint_states` from ADVRF's best-effort
sensor-data QoS to the conventional reliable `/joint_states` topic used by Robot
State Publisher and MoveIt. The input can be overridden with
`joint_states_topic:=...`.

Trajectory execution is disabled by default. Enable it only after starting
`FollowJointTrajectory` action servers whose names and joints match the controller
configuration exported by `ecat-miranda-config`:

```bash
ros2 launch miranda_advrf_bringup moveit.launch.py \
  allow_trajectory_execution:=true
```
