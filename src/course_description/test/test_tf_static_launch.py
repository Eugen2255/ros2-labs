"""Launch-тест: robot_state_publisher, профиль /tf_static и поздние подписчики."""

import os
import time
import unittest

from ament_index_python.packages import get_package_share_directory
import launch
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import launch_testing
import launch_testing.actions
import launch_testing.asserts
import pytest
import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from tf2_msgs.msg import TFMessage
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener

# Отдельный домен: тест не пересекается с вручную запущенной моделью.
os.environ['ROS_DOMAIN_ID'] = '88'

SENSORS = {'camera_link', 'lidar_link', 'imu_link'}
SENSOR_POSITION = (0.28, 0.0, 0.38)
TIMEOUT_S = 15.0


@pytest.mark.launch_test
def generate_test_description():
    launch_file = os.path.join(
        get_package_share_directory('course_description'), 'launch', 'display.launch.py')
    return launch.LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_file),
            launch_arguments={'rviz': 'false'}.items()),
        launch_testing.actions.ReadyToTest(),
    ])


class TestTfStatic(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('tf_static_probe')

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

    def _wait_publisher(self):
        self.assertTrue(self._spin_until(
            lambda: self.node.get_publishers_info_by_topic('/tf_static')))
        time.sleep(1.0)  # подписчики ниже подключаются заведомо позже публикации

    def _late_subscription(self, durability):
        received = []
        subscription = self.node.create_subscription(
            TFMessage, '/tf_static', received.append,
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=durability))
        return subscription, received

    def test_single_publisher_reliable_transient_local(self):
        self._wait_publisher()
        (info,) = self.node.get_publishers_info_by_topic('/tf_static')
        self.assertEqual(info.node_name, 'robot_state_publisher')
        self.assertEqual(info.qos_profile.reliability, ReliabilityPolicy.RELIABLE)
        self.assertEqual(info.qos_profile.durability, DurabilityPolicy.TRANSIENT_LOCAL)

    def test_late_transient_local_subscriber_gets_sensor_frames(self):
        self._wait_publisher()
        subscription, received = self._late_subscription(DurabilityPolicy.TRANSIENT_LOCAL)
        try:
            self.assertTrue(self._spin_until(lambda: received))
            transforms = {t.child_frame_id: t for t in received[0].transforms}
            self.assertEqual(set(transforms), SENSORS)
            for child, transform in transforms.items():
                self.assertEqual(transform.header.frame_id, 'base_link', child)
                t = transform.transform.translation
                self.assertEqual((t.x, t.y, t.z), SENSOR_POSITION, child)
        finally:
            self.node.destroy_subscription(subscription)

    def test_late_volatile_subscriber_gets_nothing(self):
        self._wait_publisher()
        subscription, received = self._late_subscription(DurabilityPolicy.VOLATILE)
        try:
            self._spin_until(lambda: received, timeout=3.0)
            self.assertEqual(received, [])
        finally:
            self.node.destroy_subscription(subscription)

    def test_tf2_lookup_base_link_to_lidar(self):
        buffer = Buffer()
        listener = TransformListener(buffer, self.node, spin_thread=False)
        try:
            self.assertTrue(self._spin_until(
                lambda: buffer.can_transform('base_link', 'lidar_link', Time())))
            t = buffer.lookup_transform('base_link', 'lidar_link', Time()).transform.translation
            self.assertEqual((t.x, t.y, t.z), SENSOR_POSITION)
        finally:
            listener.unregister()


@launch_testing.post_shutdown_test()
class TestShutdown(unittest.TestCase):

    def test_robot_state_publisher_exits_cleanly(self, proc_info):
        launch_testing.asserts.assertExitCodes(proc_info)
