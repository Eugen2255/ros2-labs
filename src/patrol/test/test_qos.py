from patrol.qos import reliability_policy, SENSOR_DEPTH, sensor_qos
import pytest
from rclpy.qos import HistoryPolicy, ReliabilityPolicy


def test_reliability_names():
    assert reliability_policy('reliable') == ReliabilityPolicy.RELIABLE
    assert reliability_policy('best_effort') == ReliabilityPolicy.BEST_EFFORT


@pytest.mark.parametrize('name', ['', 'RELIABLE', 'best-effort', 'system_default'])
def test_unknown_reliability_rejected(name):
    with pytest.raises(ValueError, match='reliability='):
        reliability_policy(name)


def test_sensor_qos_profile():
    qos = sensor_qos('best_effort')
    assert qos.reliability == ReliabilityPolicy.BEST_EFFORT
    assert qos.history == HistoryPolicy.KEEP_LAST
    assert qos.depth == SENSOR_DEPTH == 10
    assert sensor_qos('reliable').reliability == ReliabilityPolicy.RELIABLE
