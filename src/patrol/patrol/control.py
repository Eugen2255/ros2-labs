"""Логика команды патрулирования и проверка параметров без зависимостей от ROS."""

import math
from typing import NamedTuple, Optional

LINEAR_SPEED = 0.5
ANGULAR_SPEED = 0.3
PUBLISH_HZ = 10.0

DEFAULTS = {
    'linear_speed': LINEAR_SPEED,
    'turn_rate': ANGULAR_SPEED,
    'publish_hz': PUBLISH_HZ,
}

# Допустимые диапазоны включительно: м/с, рад/с, Гц.
LIMITS = {
    'linear_speed': (0.0, 1.0),
    'turn_rate': (-1.0, 1.0),
    'publish_hz': (1.0, 30.0),
}


class Command(NamedTuple):
    """Скорости, которые нода кладёт в Twist."""

    linear_x: float
    angular_z: float


STOP = Command(0.0, 0.0)


def compute_command(
    pose: Optional[object],
    linear_speed: float = LINEAR_SPEED,
    turn_rate: float = ANGULAR_SPEED,
) -> Command:
    """
    Вернуть команду по последней известной позе.

    Пока поза не получена, робот стоит: нельзя ехать, не зная, где он.
    После первой позы — движение по дуге с заданными скоростями.
    """
    if pose is None:
        return STOP
    return Command(linear_speed, turn_rate)


def check_parameter(name: str, value: object) -> Optional[str]:
    """Вернуть причину отказа для значения параметра или None, если оно допустимо."""
    if name not in LIMITS:
        return f'{name}: неизвестный параметр'
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f'{name}={value!r}: нужно число'
    if not math.isfinite(value):
        return f'{name}={value}: нужно конечное число'
    low, high = LIMITS[name]
    if not low <= value <= high:
        return f'{name}={value}: вне диапазона [{low}, {high}]'
    return None


def timer_period(publish_hz: float) -> float:
    """Период таймера в секундах для частоты публикации."""
    return 1.0 / publish_hz
