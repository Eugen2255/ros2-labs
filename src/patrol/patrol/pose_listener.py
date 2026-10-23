"""Нода pose_listener: подписчик sensor_pose с надёжностью из параметра reliability."""

from typing import Optional

from patrol.qos import sensor_qos
from patrol.runner import run
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.event_handler import QoSRequestedIncompatibleQoSInfo, SubscriptionEventCallbacks
from rclpy.node import Node
from rclpy.qos import QoSPolicyKind
from turtlesim_msgs.msg import Pose

REPORT_PERIOD_S = 2.0


class PoseListener(Node):
    """Считает полученные позы и раз в REPORT_PERIOD_S пишет счётчик в лог."""

    def __init__(self) -> None:
        super().__init__('pose_listener')
        self._reliability: str = self.declare_parameter(
            'reliability', 'best_effort',
            ParameterDescriptor(
                description='Надёжность подписки: reliable или best_effort',
                read_only=True)).value
        self._total = 0
        self._last_reported = 0
        self._subscription = self.create_subscription(
            Pose, 'sensor_pose', self._on_pose, sensor_qos(self._reliability),
            event_callbacks=SubscriptionEventCallbacks(
                incompatible_qos=self._on_incompatible_qos))
        self.create_timer(REPORT_PERIOD_S, self._report)
        self.get_logger().info(
            f'subscribed to {self._subscription.topic_name} ({self._reliability})')

    def _on_pose(self, msg: Pose) -> None:
        self._total += 1

    def _on_incompatible_qos(self, event: QoSRequestedIncompatibleQoSInfo) -> None:
        policy = QoSPolicyKind(event.last_policy_kind).name
        self.get_logger().warning(
            f'incompatible QoS with a publisher on {self._subscription.topic_name}: '
            f'{policy} (requested {self._reliability}); messages will not be delivered')

    def _report(self) -> None:
        received = self._total - self._last_reported
        self._last_reported = self._total
        self.get_logger().info(
            f'received {received} messages in {REPORT_PERIOD_S:.0f} s '
            f'(total {self._total}, {self._reliability})')


def main(args: Optional[list[str]] = None) -> None:
    run(PoseListener, args)


if __name__ == '__main__':
    main()
