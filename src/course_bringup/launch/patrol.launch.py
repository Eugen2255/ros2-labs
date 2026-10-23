"""Вся система одной командой: turtlesim, patrol, pose_relay, pose_listener и запись MCAP."""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, ExecuteProcess, GroupAction, IncludeLaunchDescription, LogInfo)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    namespace = LaunchConfiguration('namespace')
    record = LaunchConfiguration('record')
    bag_dir = LaunchConfiguration('bag_dir')
    reliability = LaunchConfiguration('subscriber_reliability')

    arguments = [
        DeclareLaunchArgument(
            'namespace', default_value='robot_a',
            description='Пространство имён для patrol, pose_relay и pose_listener'),
        DeclareLaunchArgument(
            'record', default_value='false', choices=['true', 'false'],
            description='Записывать /<namespace>/sensor_pose в MCAP'),
        DeclareLaunchArgument(
            'bag_dir', default_value='evidence/pr05/bag',
            description='Каталог записи (не должен существовать)'),
        DeclareLaunchArgument(
            'subscriber_reliability', default_value='best_effort',
            choices=['reliable', 'best_effort'],
            description='Надёжность подписки pose_listener на sensor_pose'),
    ]

    # turtlesim остаётся глобальным: /turtlesim, /turtle1/pose, /turtle1/cmd_vel.
    sim = IncludeLaunchDescription(PythonLaunchDescriptionSource(
        PathJoinSubstitution([FindPackageShare('turtle_bringup'), 'launch', 'sim.launch.py'])))

    # Всё в группе получает пространство имён; scoped по умолчанию — за группу оно не выходит.
    robot = GroupAction([
        PushRosNamespace(namespace),
        Node(
            package='patrol', executable='patrol', output='screen',
            # Относительный cmd_vel стал бы /<namespace>/cmd_vel — turtlesim его не слушает.
            remappings=[('cmd_vel', '/turtle1/cmd_vel')]),
        Node(package='patrol', executable='pose_relay', output='screen'),
        Node(
            package='patrol', executable='pose_listener', output='screen',
            parameters=[{'reliability': reliability}]),
    ])

    recorder = ExecuteProcess(
        cmd=['ros2', 'bag', 'record', '-s', 'mcap', '-o', bag_dir,
             '--topics', ['/', namespace, '/sensor_pose']],
        output='screen',
        condition=IfCondition(record))

    return LaunchDescription([
        *arguments,
        LogInfo(msg=['namespace=/', namespace, ' subscriber_reliability=', reliability,
                     ' record=', record, ' bag_dir=', bag_dir]),
        sim,
        robot,
        recorder,
    ])
