"""Нода patrol: хранит последнюю позу черепахи и по таймеру публикует Twist."""

import signal
from typing import Optional

from geometry_msgs.msg import Twist
from patrol.control import (
    check_parameter, compute_command, DEFAULTS, LIMITS, timer_period)
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.signals import SignalHandlerOptions
from turtlesim_msgs.msg import Pose

DESCRIPTIONS = {
    'linear_speed': 'Линейная скорость после получения позы, м/с',
    'turn_rate': 'Угловая скорость после получения позы, рад/с',
    'publish_hz': 'Частота публикации команды (период таймера 1/publish_hz), Гц',
}


def _descriptor(name: str) -> ParameterDescriptor:
    # Диапазон только в описании: floating_point_range заставил бы rclpy отклонять
    # значения до нашего callback, а проверка должна быть в коде ноды.
    low, high = LIMITS[name]
    return ParameterDescriptor(
        description=f'{DESCRIPTIONS[name]}; допустимо [{low}, {high}], конечное число')


class Patrol(Node):
    """Подписка на /turtle1/pose, таймер publish_hz и издатель в относительный cmd_vel."""

    def __init__(self) -> None:
        super().__init__('patrol')
        for name, default in DEFAULTS.items():
            self.declare_parameter(name, default, _descriptor(name))
        values = {name: self.get_parameter(name).value for name in DEFAULTS}
        for name, value in values.items():
            reason = check_parameter(name, value)
            if reason is not None:
                raise ValueError(f'недопустимое начальное значение: {reason}')
        self._linear_speed: float = values['linear_speed']
        self._turn_rate: float = values['turn_rate']
        self._publish_hz: float = values['publish_hz']

        self._pose: Optional[Pose] = None
        # Относительное имя: без remap это /cmd_vel, а не /turtle1/cmd_vel.
        self._publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.create_subscription(Pose, '/turtle1/pose', self._on_pose, 10)
        self._timer = self.create_timer(timer_period(self._publish_hz), self._on_timer)

        # Проверка до изменения: при отказе ни значение, ни таймер не меняются.
        self.add_on_set_parameters_callback(self._validate_parameters)
        # Применение после успешной проверки.
        self.add_post_set_parameters_callback(self._apply_parameters)
        self.get_logger().info(
            f'publishing to {self._publisher.topic_name} at {self._publish_hz} Hz, '
            'waiting for /turtle1/pose')

    @property
    def publish_hz(self) -> float:
        return self._publish_hz

    @property
    def timer_period_s(self) -> float:
        return self._timer.timer_period_ns / 1e9

    def _validate_parameters(self, params: list[Parameter]) -> SetParametersResult:
        for param in params:
            if param.name not in LIMITS:
                continue
            reason = check_parameter(param.name, param.value)
            if reason is not None:
                self.get_logger().warning(f'rejected {reason}')
                return SetParametersResult(successful=False, reason=reason)
        return SetParametersResult(successful=True)

    def _apply_parameters(self, params: list[Parameter]) -> None:
        for param in params:
            if param.name == 'linear_speed':
                self._linear_speed = param.value
            elif param.name == 'turn_rate':
                self._turn_rate = param.value
            elif param.name == 'publish_hz':
                self._restart_timer(param.value)
            else:
                continue
            self.get_logger().info(f'{param.name} = {param.value}')

    def _restart_timer(self, publish_hz: float) -> None:
        # Старый таймер уничтожается, новый создаётся: одновременно работает один.
        self.destroy_timer(self._timer)
        self._timer = self.create_timer(timer_period(publish_hz), self._on_timer)
        self._publish_hz = publish_hz

    def _on_pose(self, msg: Pose) -> None:
        if self._pose is None:
            self.get_logger().info(
                f'first pose: x={msg.x:.3f} y={msg.y:.3f} theta={msg.theta:.3f}')
        self._pose = msg

    def _on_timer(self) -> None:
        command = compute_command(self._pose, self._linear_speed, self._turn_rate)
        msg = Twist()
        msg.linear.x = command.linear_x
        msg.angular.z = command.angular_z
        self._publisher.publish(msg)


def main(args: Optional[list[str]] = None) -> None:
    # Ctrl+C обрабатывает Python (KeyboardInterrupt из spin), а не обработчик rclpy:
    # иначе контекст гасится во время ожидания и spin падает с RCLError.
    # Обработчик ставится явно: у фонового процесса SIGINT может быть унаследован
    # как игнорируемый, и тогда Python сам KeyboardInterrupt не включает.
    signal.signal(signal.SIGINT, signal.default_int_handler)
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = Patrol()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
