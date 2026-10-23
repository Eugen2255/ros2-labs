"""QoS потока sensor_pose: выбор надёжности по имени из параметра или launch-аргумента."""

from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

RELIABILITY = {
    'reliable': ReliabilityPolicy.RELIABLE,
    'best_effort': ReliabilityPolicy.BEST_EFFORT,
}
SENSOR_DEPTH = 10


def reliability_policy(name: str) -> ReliabilityPolicy:
    """Вернуть политику надёжности по имени или бросить ValueError."""
    try:
        return RELIABILITY[name]
    except KeyError:
        raise ValueError(
            f'reliability={name!r}: ожидается одно из {sorted(RELIABILITY)}') from None


def sensor_qos(reliability: str) -> QoSProfile:
    """Профиль для sensor_pose: последние SENSOR_DEPTH сообщений, заданная надёжность."""
    return QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=SENSOR_DEPTH,
        reliability=reliability_policy(reliability))
