"""Нода zero_joint_states: нулевые положения подвижных сочленений для отображения колёс."""

import signal
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import JointState

RATE_HZ = 10.0


class ZeroJointStates(Node):
    """Публикует /joint_states с нулями: robot_state_publisher выводит колёса в /tf."""

    def __init__(self) -> None:
        super().__init__('zero_joint_states')
        self._names: list[str] = list(
            self.declare_parameter('joint_names', ['']).value)
        self._publisher = self.create_publisher(JointState, 'joint_states', 10)
        self.create_timer(1.0 / RATE_HZ, self._publish)
        self.get_logger().info(f'publishing zero positions for {self._names}')

    def _publish(self) -> None:
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self._names
        msg.position = [0.0] * len(self._names)
        self._publisher.publish(msg)


def main(args: Optional[list[str]] = None) -> None:
    # Ctrl+C → KeyboardInterrupt из spin (таймер 10 Гц регулярно возвращает управление
    # в Python), затем штатное завершение с кодом 0.
    signal.signal(signal.SIGINT, signal.default_int_handler)
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = ZeroJointStates()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
