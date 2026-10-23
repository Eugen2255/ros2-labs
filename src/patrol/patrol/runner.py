"""Общий жизненный цикл нод пакета: init, spin, корректное завершение по Ctrl+C."""

import signal
from typing import Callable, Optional

import rclpy
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions

# Как часто spin возвращается в Python, чтобы сработал обработчик Ctrl+C.
SPIN_TIMEOUT_S = 0.1


def run(node_factory: Callable[[], Node], args: Optional[list[str]] = None) -> None:
    # Ctrl+C обрабатывает Python (KeyboardInterrupt), а не обработчик rclpy:
    # иначе контекст гасится во время ожидания и spin падает с RCLError.
    # Обработчик ставится явно: у фонового процесса SIGINT может быть унаследован
    # как игнорируемый, и тогда Python сам KeyboardInterrupt не включает.
    signal.signal(signal.SIGINT, signal.default_int_handler)
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = node_factory()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        # Python выполняет обработчик сигнала только между своими инструкциями.
        # Бесконечный rclpy.spin ждёт событий внутри C-кода, и нода без таймера
        # (pose_relay, когда поток позы прекратился) не реагировала бы на Ctrl+C.
        while rclpy.ok():
            executor.spin_once(timeout_sec=SPIN_TIMEOUT_S)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()
