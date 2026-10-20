#!/usr/bin/env python3
"""Bridge ADVRF sensor-data QoS to the reliable ROS joint_states convention."""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState


class JointStateRelay(Node):
    def __init__(self):
        super().__init__("joint_state_relay")

        input_topic = self.declare_parameter(
            "input_topic", "/advrf/miranda/rx/joint_states"
        ).value
        output_topic = self.declare_parameter("output_topic", "/joint_states").value
        self._restamp = self.declare_parameter("restamp", True).value

        output_qos = QoSProfile(depth=10)
        output_qos.reliability = ReliabilityPolicy.RELIABLE

        self._publisher = self.create_publisher(JointState, output_topic, output_qos)
        self._subscription = self.create_subscription(
            JointState, input_topic, self._relay, qos_profile_sensor_data
        )

        self.get_logger().info(
            f"Relaying {input_topic} (sensor-data QoS) to {output_topic} "
            "(reliable QoS)"
        )

    def _relay(self, message: JointState) -> None:
        if self._restamp:
            message.header.stamp = self.get_clock().now().to_msg()
        self._publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = JointStateRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
