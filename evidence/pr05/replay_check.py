"""Сверить позы, полученные echo (qos-after.txt), с содержимым записи evidence/pr05/bag.

Запуск из корня workspace: python3 evidence/pr05/replay_check.py
"""
import re

from rclpy.serialization import deserialize_message
import rosbag2_py
from turtlesim_msgs.msg import Pose

BAG = 'evidence/pr05/bag'
ECHO = 'evidence/pr05/qos-after.txt'


def echoed_poses(path):
    text = open(path, encoding='utf-8').read()
    blocks = re.findall(r'# ([^\n]+)\nx: (\S+)\ny: (\S+)\ntheta: (\S+)', text)
    return [(label, float(x), float(y), float(t)) for label, x, y, t in blocks]


def recorded_poses(uri):
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id='mcap'),
                rosbag2_py.ConverterOptions('', ''))
    poses = []
    while reader.has_next():
        _, data, _ = reader.read_next()
        msg = deserialize_message(data, Pose)
        poses.append((msg.x, msg.y, msg.theta))
    return poses


poses = recorded_poses(BAG)
print(f'$ python3 evidence/pr05/replay_check.py  # сверка echo из {ECHO} с {BAG}')
print(f'сообщений в записи: {len(poses)}; первое x={poses[0][0]:.6f} y={poses[0][1]:.6f}; '
      f'последнее x={poses[-1][0]:.6f} y={poses[-1][1]:.6f}')
for label, x, y, theta in echoed_poses(ECHO):
    hits = [i for i, pose in enumerate(poses) if pose == (x, y, theta)]
    where = f'найдено: сообщение №{hits[0] + 1} из {len(poses)}' if hits else 'в записи нет'
    print(f'echo ({label}): x={x} y={y} theta={theta} -> {where}')
