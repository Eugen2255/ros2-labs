"""Проверка параметров на настоящей ноде: отказ не меняет значение и таймер."""

import math

from patrol.patrol import Patrol
import pytest
import rclpy
from rclpy.parameter import Parameter


@pytest.fixture
def node():
    rclpy.init()
    patrol = Patrol()
    yield patrol
    patrol.destroy_node()
    rclpy.try_shutdown()


def _set(node, name, value):
    return node.set_parameters([Parameter(name, value=value)])[0]


def test_defaults(node):
    assert node.get_parameter('publish_hz').value == 10.0
    assert node.timer_period_s == pytest.approx(0.1)
    assert len(list(node.timers)) == 1


def test_publish_hz_10_to_5_recreates_single_timer(node):
    old_timer = node._timer
    result = _set(node, 'publish_hz', 5.0)
    assert result.successful
    assert node.get_parameter('publish_hz').value == 5.0
    assert node.publish_hz == 5.0
    assert node.timer_period_s == pytest.approx(0.2)
    assert node._timer is not old_timer
    assert len(list(node.timers)) == 1


@pytest.mark.parametrize('value', [0.0, -5.0, math.nan])
def test_invalid_publish_hz_rejected_state_kept(node, value):
    old_timer = node._timer
    result = _set(node, 'publish_hz', value)
    assert not result.successful
    assert result.reason.startswith('publish_hz')
    assert node.get_parameter('publish_hz').value == 10.0
    assert node.publish_hz == 10.0
    assert node._timer is old_timer
    assert node.timer_period_s == pytest.approx(0.1)
    assert len(list(node.timers)) == 1


def test_speed_parameters_change_command(node):
    assert _set(node, 'linear_speed', 1.0).successful
    assert _set(node, 'turn_rate', -0.5).successful
    assert not _set(node, 'linear_speed', 2.0).successful
    assert node.get_parameter('linear_speed').value == 1.0
    assert (node._linear_speed, node._turn_rate) == (1.0, -0.5)
