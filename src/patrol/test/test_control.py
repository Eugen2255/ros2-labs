import math

from patrol.control import (
    ANGULAR_SPEED, check_parameter, compute_command, DEFAULTS, LINEAR_SPEED, STOP,
    timer_period)
import pytest
from turtlesim_msgs.msg import Pose


def test_no_pose_gives_stop():
    assert compute_command(None) == STOP
    assert compute_command(None).linear_x == 0.0
    assert compute_command(None).angular_z == 0.0


def test_pose_gives_patrol_command():
    pose = Pose(x=5.544445, y=5.544445, theta=0.0)
    command = compute_command(pose)
    assert command.linear_x == LINEAR_SPEED == 0.5
    assert command.angular_z == ANGULAR_SPEED == 0.3


def test_command_does_not_depend_on_pose_values():
    first = compute_command(Pose(x=1.0, y=1.0, theta=0.0))
    second = compute_command(Pose(x=10.0, y=2.0, theta=3.0))
    assert first == second


def test_command_uses_parameters():
    command = compute_command(Pose(), linear_speed=1.0, turn_rate=-0.5)
    assert command == (1.0, -0.5)
    assert compute_command(None, linear_speed=1.0, turn_rate=-0.5) == STOP


def test_defaults_are_valid():
    assert DEFAULTS == {'linear_speed': 0.5, 'turn_rate': 0.3, 'publish_hz': 10.0}
    for name, value in DEFAULTS.items():
        assert check_parameter(name, value) is None


def test_publish_hz_change_10_to_5():
    assert check_parameter('publish_hz', 5.0) is None
    assert timer_period(10.0) == pytest.approx(0.1)
    assert timer_period(5.0) == pytest.approx(0.2)


@pytest.mark.parametrize('value', [0.0, 0, -5.0, math.nan, math.inf, 0.5, 30.5])
def test_publish_hz_invalid_rejected(value):
    reason = check_parameter('publish_hz', value)
    assert reason is not None
    assert reason.startswith('publish_hz')


def test_publish_hz_zero_reason():
    assert check_parameter('publish_hz', 0.0) == 'publish_hz=0.0: вне диапазона [1.0, 30.0]'


def test_publish_hz_nan_reason():
    assert check_parameter('publish_hz', math.nan) == 'publish_hz=nan: нужно конечное число'


@pytest.mark.parametrize('name,value', [
    ('publish_hz', 1.0), ('publish_hz', 30.0), ('publish_hz', 7),
    ('linear_speed', 0.0), ('linear_speed', 1.0),
    ('turn_rate', -1.0), ('turn_rate', 1.0),
])
def test_boundaries_accepted(name, value):
    assert check_parameter(name, value) is None


@pytest.mark.parametrize('name,value', [
    ('linear_speed', -0.1), ('linear_speed', 1.1), ('linear_speed', math.nan),
    ('turn_rate', -1.5), ('turn_rate', 2.0), ('turn_rate', -math.inf),
    ('publish_hz', 'fast'), ('publish_hz', True), ('unknown', 1.0),
])
def test_other_invalid_rejected(name, value):
    assert check_parameter(name, value) is not None
