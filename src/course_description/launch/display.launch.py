"""robot_state_publisher с развёрнутым Xacro и (по желанию) RViz."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import (
    Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

# Подвижные сочленения: без joint_states их звенья не появятся в /tf.
MOVABLE_JOINTS = [
    'front_left_steering_joint', 'front_right_steering_joint',
    'front_left_wheel_joint', 'front_right_wheel_joint',
    'rear_left_wheel_joint', 'rear_right_wheel_joint',
]


def generate_launch_description():
    share = FindPackageShare('course_description')
    model = LaunchConfiguration('model')

    # xacro разворачивает макросы и переменные в обычный URDF прямо при запуске.
    robot_description = ParameterValue(
        Command([FindExecutable(name='xacro'), ' ', model]), value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument(
            'model', default_value=PathJoinSubstitution([share, 'urdf', 'vehicle.urdf.xacro']),
            description='Путь к Xacro-описанию робота'),
        DeclareLaunchArgument(
            'rviz', default_value='true', choices=['true', 'false'],
            description='Открыть RViz с Fixed Frame=base_link'),
        DeclareLaunchArgument(
            'joint_states', default_value='false', choices=['true', 'false'],
            description='Публиковать нулевые положения колёс и руля (иначе их нет в /tf)'),

        # Единственный владелец всех преобразований модели: /tf_static и /tf.
        Node(
            package='robot_state_publisher', executable='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}]),

        # Публикует только углы сочленений; преобразования по ним считает robot_state_publisher.
        Node(
            package='course_description', executable='zero_joint_states', output='screen',
            parameters=[{'joint_names': MOVABLE_JOINTS}],
            condition=IfCondition(LaunchConfiguration('joint_states'))),

        Node(
            package='rviz2', executable='rviz2', output='screen',
            arguments=['-d', PathJoinSubstitution([share, 'rviz', 'vehicle.rviz'])],
            condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
