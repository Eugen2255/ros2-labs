"""Нода pose_relay: пересылает /turtle1/pose в относительный sensor_pose с QoS best_effort."""

from typing import Optional

from patrol.qos import sensor_qos
from patrol.runner import run
from rclpy.node import Node
from turtlesim_msgs.msg import Pose


class PoseRelay(Node):
    """Имитирует датчик: поток позы с политикой best_effort, как у типичных сенсоров."""

    def __init__(self) -> None:
        super().__init__('pose_relay')
        self._publisher = self.create_publisher(Pose, 'sensor_pose', sensor_qos('best_effort'))
        self.create_subscription(Pose, '/turtle1/pose', self._publisher.publish, 10)
        self.get_logger().info(
            f'relaying /turtle1/pose -> {self._publisher.topic_name} (best_effort)')


def main(args: Optional[list[str]] = None) -> None:
    run(PoseRelay, args)


if __name__ == '__main__':
    main()
