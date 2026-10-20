# Miranda ADVRF bringup

This package launches RViz and MoveIt directly from the ROS 2 resources exported
by the `ecat-miranda-config` branch `moveit/advrf_middleware`.

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
State Publisher and MoveIt.
