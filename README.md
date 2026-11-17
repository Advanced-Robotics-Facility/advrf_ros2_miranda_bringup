# Miranda - Quick Use


## Global Architecture

![miranda_ros2_bridge-global_architecture.drawio](.doc/miranda_ros2_bridge-global_architecture.drawio.png)

## Docker Installation 

```bash
# clone repo branch: ec_ros2/miranda
git clone https://github.com/Advanced-Robotics-Facility/advrf-dev-environment/tree/ec_ros2/miranda

# go to docker folder
cd docker/

# build​
docker compose -f compose.build.yaml build workspace​

# start the docker​
docker compose up –d ​

# enter in docker​
docker compose exec workspace bash​

# … after work... stop the docker​
docker compose down​
```

## Use Docker

To use the robot
- you shoud to have `ethercat + ros2 bridge + ros2 part`
- warning with `ROS_DOMAIN_ID`, specially if you use the robot, by default on the robot is 42

You can't see the topic on your pc once you launch next demos:
- Good ip ? same of the robot
- Good `ROS_DOMAIN_ID` ? same of the robot
- `Repl` is started on the robot ?
- `ros2 bridge` is started on the robot ? 
- try to restart the ros2 daemon: `ros2 daemon stop && ros2 daemon start`

warning: start the same `control_mode` both side there is no check between same, so be careful, because the `control_mode` is used ros2 side to know initial gains from config file.

### Use Docker in dummy mode

```bash
# start the docker​
docker compose up –d ​
```

#### Setup Ethercat Communication to ROS2 (By Docker)

```bash
## start repl in dummy mode (-d), to run fake ethercat motors
docker compose exec workspace bash​
repl -d
```

```bash
## start ros2 bridge
docker compose exec workspace bash​
ros2 launch advrf_ros2_miranda_bringup bridge.launch.py active_tx_on_first_msg:=true control_mode:=position
```
active_tx_on_first_msg:={true|false} 
control_mode:={position|impedance}

if you put `active_tx_on_first_msg:=false`, start the service 
```bash
ros2 service call /advrf/miranda/ecat/set_active_tx std_srvs/srv/SetBool '{data: true}'
```

#### Launch demos

```bash
## DEMO JOY
## start ros2 bridge
docker compose exec workspace bash​
ros2 launch advrf_ros2_miranda_bringup miranda.launch.py use_joy:=true start_bridge:=false control_mode:=position
```
start_bridge:={false|true} 
control_mode:={position|impedance}


```bash
## DEMO MOVEIT
## start ros2 bridge
docker compose exec workspace bash​
ros2 launch advrf_ros2_miranda_bringup moveit.launch.py start_bridge:=false control_mode:=position
```
start_bridge:={false|true} 
control_mode:={position|impedance}


```bash
## DEMO gravity compensation
## start ros2 bridge
docker compose exec workspace bash​
ros2 launch advrf_ros2_miranda_bringup gravity_compensation.launch.py start_bridge:=false use_rviz:=true 
```
start_bridge:={false|true} 


### Use Docker with the robot


```bash
# start the docker​
docker compose up –d ​
```

#### Setup Ethercat Communication to ROS2 (By SSH)

```bash
## start repl in the robot, password: pitagora
ssh embedded@192.168.10.101
repl 
```

```bash
## start ros2 bridge
ssh embedded@192.168.10.101
ros2 launch advrf_ros2_miranda_bringup bridge.launch.py active_tx_on_first_msg:=true control_mode:=position
```
active_tx_on_first_msg:={true|false} 
control_mode:={position|impedance}

:warning: replace `192.168.10.101` by the good robot IP.

#### Launch demos

```bash
## DEMO JOY
## start ros2 bridge
docker compose exec workspace bash​
ros2 launch advrf_ros2_miranda_bringup miranda.launch.py use_joy:=true start_bridge:=false control_mode:=position
```
start_bridge:={false|true} 
control_mode:={position|impedance}


```bash
## DEMO MOVEIT
## start ros2 bridge
docker compose exec workspace bash​
ros2 launch advrf_ros2_miranda_bringup moveit.launch.py start_bridge:=false control_mode:=position
```
start_bridge:={false|true} 
control_mode:={position|impedance}


```bash
## DEMO gravity compensation
## start ros2 bridge
docker compose exec workspace bash​
ros2 launch advrf_ros2_miranda_bringup gravity_compensation.launch.py start_bridge:=false use_rviz:=true 
```
start_bridge:={false|true} 