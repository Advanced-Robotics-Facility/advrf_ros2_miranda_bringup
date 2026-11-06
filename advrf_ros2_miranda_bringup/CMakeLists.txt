cmake_minimum_required(VERSION 3.22)
project(advrf_ros2_miranda_bringup)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch config urdf srdf rviz
  DESTINATION share/${PROJECT_NAME}
)

install(FILES README.md DESTINATION share/${PROJECT_NAME})

ament_package()
