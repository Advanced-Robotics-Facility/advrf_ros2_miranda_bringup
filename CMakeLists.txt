cmake_minimum_required(VERSION 3.22)
project(miranda_advrf_bringup)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch rviz
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/joint_state_relay.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  FILES README.md
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
