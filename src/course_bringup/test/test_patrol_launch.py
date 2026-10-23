"""Launch-тест patrol.launch.py: имена, QoS, remap и корректное завершение процессов."""

import os
import time
import unittest

from ament_index_python.packages import get_package_share_directory
import launch
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
import launch_testing
import launch_testing.actions
import launch_testing.asserts
import pytest
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from turtlesim_msgs.msg import Pose

# Отдельный домен: тест не пересекается с turtlesim, запущенным вручную.
os.environ['ROS_DOMAIN_ID'] = '87'

NAMESPACE = 'robot_t'
SENSOR_TOPIC = f'/{NAMESPACE}/sensor_pose'
TIMEOUT_S = 20.0


@pytest.mark.launch_test
def generate_test_description():
    launch_file = os.path.join(
        get_package_share_directory('course_bringup'), 'launch', 'patrol.launch.py')
    return launch.LaunchDescription([
        SetEnvironmentVariable('QT_QPA_PLATFORM', 'offscreen'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_file),
            launch_arguments={
                'namespace': NAMESPACE,
                'record': 'false',
                'subscriber_reliability': 'best_effort',
            }.items()),
        launch_testing.actions.ReadyToTest(),
    ])


class TestRunningSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('launch_probe')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def _spin_until(self, condition, timeout=TIMEOUT_S):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if condition():
                return True
            rclpy.spin_once(self.node, timeout_sec=0.1)
        return condition()

    def test_nodes_in_namespace_turtlesim_global(self):
        expected = {
            ('turtlesim', '/'),
            ('patrol', f'/{NAMESPACE}'),
            ('pose_relay', f'/{NAMESPACE}'),
            ('pose_listener', f'/{NAMESPACE}'),
        }
        found = self._spin_until(
            lambda: expected <= set(self.node.get_node_names_and_namespaces()))
        self.assertTrue(found, self.node.get_node_names_and_namespaces())

    def test_patrol_command_remapped_to_turtlesim(self):
        def patrol_publishes():
            return any(
                (info.node_name, info.node_namespace) == ('patrol', f'/{NAMESPACE}')
                for info in self.node.get_publishers_info_by_topic('/turtle1/cmd_vel'))
        self.assertTrue(self._spin_until(patrol_publishes))
        self.assertEqual(self.node.get_publishers_info_by_topic(f'/{NAMESPACE}/cmd_vel'), [])

    def test_sensor_pose_publisher_is_best_effort(self):
        self.assertTrue(self._spin_until(
            lambda: self.node.get_publishers_info_by_topic(SENSOR_TOPIC)))
        (info,) = self.node.get_publishers_info_by_topic(SENSOR_TOPIC)
        self.assertEqual(info.node_name, 'pose_relay')
        self.assertEqual(info.qos_profile.reliability, ReliabilityPolicy.BEST_EFFORT)

    def test_best_effort_receives_reliable_does_not(self):
        received = {'reliable': [], 'best_effort': []}
        subscriptions = [
            self.node.create_subscription(
                Pose, SENSOR_TOPIC, received[name].append,
                QoSProfile(depth=10, reliability=policy))
            for name, policy in (('reliable', ReliabilityPolicy.RELIABLE),
                                 ('best_effort', ReliabilityPolicy.BEST_EFFORT))]
        try:
            self.assertTrue(self._spin_until(lambda: len(received['best_effort']) >= 20))
            self.assertEqual(received['reliable'], [])
        finally:
            for subscription in subscriptions:
                self.node.destroy_subscription(subscription)


@launch_testing.post_shutdown_test()
class TestShutdown(unittest.TestCase):

    def test_all_processes_exit_cleanly(self, proc_info):
        launch_testing.asserts.assertExitCodes(proc_info)
