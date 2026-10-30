"""Структура и геометрия развёрнутого vehicle.urdf.xacro."""

import math
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
import pytest
import xacro

XACRO_NAME = Path('urdf') / 'vehicle.urdf.xacro'
KIT_SDF = Path('.course-kit') / 'v1' / 'models' / 'course_ackermann' / 'model.sdf'

# Контракт дерева: у каждого звена ровно один ожидаемый родитель.
EXPECTED_PARENT = {
    'front_left_knuckle': 'base_link',
    'front_right_knuckle': 'base_link',
    'front_left_wheel': 'front_left_knuckle',
    'front_right_wheel': 'front_right_knuckle',
    'rear_left_wheel': 'base_link',
    'rear_right_wheel': 'base_link',
    'camera_link': 'base_link',
    'lidar_link': 'base_link',
    'imu_link': 'base_link',
}
SENSOR_POSITION = (0.28, 0.0, 0.38)  # м в base_link, из model.sdf
WHEELBASE, TRACK, WHEEL_RADIUS, WHEEL_WIDTH = 0.80, 0.62, 0.12, 0.07


def _xacro_path():
    source = Path(__file__).resolve().parents[1] / XACRO_NAME
    if source.is_file():
        return source
    from ament_index_python.packages import get_package_share_directory
    return Path(get_package_share_directory('course_description')) / XACRO_NAME


def _find_up(relative):
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for folder in (start, *start.parents):
            if (folder / relative).is_file():
                return folder / relative
    return None


@pytest.fixture(scope='module')
def urdf_xml():
    return xacro.process_file(str(_xacro_path())).toxml()


@pytest.fixture(scope='module')
def robot(urdf_xml):
    return ET.fromstring(urdf_xml)


def _joints(robot):
    return {joint.get('name'): joint for joint in robot.findall('joint')}


def _parent_of(robot):
    return {j.find('child').get('link'): j.find('parent').get('link')
            for j in robot.findall('joint')}


def _floats(text):
    return [float(value) for value in text.split()]


def _origin_matrix(element):
    origin = element.find('origin')
    xyz = _floats(origin.get('xyz', '0 0 0')) if origin is not None else [0.0] * 3
    rpy = _floats(origin.get('rpy', '0 0 0')) if origin is not None else [0.0] * 3
    roll, pitch, yaw = rpy
    rx = np.array([[1, 0, 0], [0, math.cos(roll), -math.sin(roll)],
                   [0, math.sin(roll), math.cos(roll)]])
    ry = np.array([[math.cos(pitch), 0, math.sin(pitch)], [0, 1, 0],
                   [-math.sin(pitch), 0, math.cos(pitch)]])
    rz = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0],
                   [0, 0, 1]])
    matrix = np.eye(4)
    matrix[:3, :3] = rz @ ry @ rx  # URDF: fixed axes roll, pitch, yaw
    matrix[:3, 3] = xyz
    return matrix


def _pose_in_base(robot, link):
    """Положение звена в base_link при нулевых углах всех сочленений."""
    by_child = {j.find('child').get('link'): j for j in robot.findall('joint')}
    matrix = np.eye(4)
    while link != 'base_link':
        joint = by_child[link]
        matrix = _origin_matrix(joint) @ matrix
        link = joint.find('parent').get('link')
    return matrix


def test_tree_has_single_root_and_no_cycles(robot):
    links = {link.get('name') for link in robot.findall('link')}
    children = [j.find('child').get('link') for j in robot.findall('joint')]
    parents = _parent_of(robot)
    assert len(children) == len(set(children)), 'у звена больше одного родителя'
    assert set(children) | set(parents.values()) <= links, 'сочленение ссылается на нет звена'
    assert links - set(children) == {'base_link'}, 'корень дерева должен быть один: base_link'
    for link in links:
        seen = set()
        while link != 'base_link':
            assert link not in seen, f'цикл через {link}'
            seen.add(link)
            link = parents[link]


def test_expected_parent_of_every_link(robot):
    assert _parent_of(robot) == EXPECTED_PARENT


@pytest.mark.parametrize('sensor', ['camera_link', 'lidar_link', 'imu_link'])
def test_sensor_pose_in_base_link(robot, sensor):
    pose = _pose_in_base(robot, sensor)
    np.testing.assert_allclose(pose[:3, 3], SENSOR_POSITION, atol=1e-9)
    np.testing.assert_allclose(pose[:3, :3], np.eye(3), atol=1e-9)


def test_wheel_layout_matches_parameters(robot):
    position = {name: _pose_in_base(robot, name)[:3, 3]
                for name in ('front_left_wheel', 'front_right_wheel',
                             'rear_left_wheel', 'rear_right_wheel')}
    assert position['front_left_wheel'][0] - position['rear_left_wheel'][0] == \
        pytest.approx(WHEELBASE)
    assert position['front_left_wheel'][1] - position['front_right_wheel'][1] == \
        pytest.approx(TRACK)
    for name in position:
        assert position[name][2] == pytest.approx(0.0), 'оси колёс на высоте base_link'
        cylinder = robot.find(f"link[@name='{name}']/collision/geometry/cylinder")
        assert float(cylinder.get('radius')) == pytest.approx(WHEEL_RADIUS)
        assert float(cylinder.get('length')) == pytest.approx(WHEEL_WIDTH)


def test_joint_types_and_axes(robot):
    joints = _joints(robot)
    for side in ('left', 'right'):
        steering = joints[f'front_{side}_steering_joint']
        assert steering.get('type') == 'revolute'
        assert _floats(steering.find('axis').get('xyz')) == [0, 0, 1]
        limit = steering.find('limit')
        assert float(limit.get('lower')) == pytest.approx(-0.55)
        assert float(limit.get('upper')) == pytest.approx(0.55)
        for axle in ('front', 'rear'):
            wheel = joints[f'{axle}_{side}_wheel_joint']
            assert wheel.get('type') == 'continuous'
            assert _floats(wheel.find('axis').get('xyz')) == [0, 1, 0]
    for sensor in ('camera', 'lidar', 'imu'):
        assert joints[f'{sensor}_joint'].get('type') == 'fixed'


@pytest.mark.parametrize('link', ['base_link', 'front_left_wheel', 'rear_right_wheel',
                                  'camera_link', 'lidar_link', 'imu_link'])
def test_visual_and_collision_are_separate(robot, link):
    element = robot.find(f"link[@name='{link}']")
    assert element.find('visual/geometry') is not None
    assert element.find('collision/geometry') is not None


def test_inertia_is_physically_possible(robot):
    for link in robot.findall('link'):
        inertial = link.find('inertial')
        assert inertial is not None, f"{link.get('name')}: нет inertial"
        mass = float(inertial.find('mass').get('value'))
        assert mass > 0
        i = {k: float(v) for k, v in inertial.find('inertia').attrib.items()}
        tensor = np.array([[i['ixx'], i['ixy'], i['ixz']],
                           [i['ixy'], i['iyy'], i['iyz']],
                           [i['ixz'], i['iyz'], i['izz']]])
        principal = np.linalg.eigvalsh(tensor)
        assert principal.min() > 0, f"{link.get('name')}: тензор не положительно определён"
        a, b, c = sorted(principal)
        assert a + b >= c - 1e-12, f"{link.get('name')}: нарушено неравенство треугольника"


def test_si_units_are_plausible(robot):
    total_mass = sum(float(m.get('value')) for m in robot.iter('mass'))
    assert 5.0 < total_mass < 50.0, 'масса в кг, а не в граммах'
    for joint in robot.findall('joint'):
        offset = np.linalg.norm(_origin_matrix(joint)[:3, 3])
        assert offset < 2.0, f"{joint.get('name')}: смещение в метрах, а не в мм"


def test_check_urdf_accepts_model(urdf_xml, tmp_path):
    if shutil.which('check_urdf') is None:
        pytest.skip('check_urdf не установлен')
    urdf = tmp_path / 'vehicle.urdf'
    urdf.write_text(urdf_xml)
    result = subprocess.run(['check_urdf', str(urdf)], capture_output=True, text=True)
    # Структурная проверка: дерево корректно как URDF. Смысл связей (кто parent
    # у сенсора) check_urdf не проверяет — это делает test_expected_parent_of_every_link.
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Successfully Parsed XML' in result.stdout
    assert 'root Link: base_link' in result.stdout


def test_dimensions_match_course_sdf(robot):
    sdf_path = _find_up(KIT_SDF)
    if sdf_path is None:
        pytest.skip('course kit с model.sdf не найден')
    model = ET.parse(sdf_path).getroot().find('model')

    def sdf_xyz(link):
        return _floats(model.find(f"link[@name='{link}']/pose").text)[:3]

    for link in ('front_left_knuckle', 'front_right_knuckle', 'rear_left_wheel',
                 'rear_right_wheel', 'camera_link', 'lidar_link', 'imu_link'):
        np.testing.assert_allclose(_pose_in_base(robot, link)[:3, 3], sdf_xyz(link), atol=1e-9)
    plugin = model.find('plugin')
    assert float(plugin.find('wheel_base').text) == pytest.approx(WHEELBASE)
    assert float(plugin.find('wheel_separation').text) == pytest.approx(TRACK)
    assert float(plugin.find('wheel_radius').text) == pytest.approx(WHEEL_RADIUS)
    body = _floats(model.find("link[@name='base_link']/collision/geometry/box/size").text)
    urdf_body = _floats(robot.find("link[@name='base_link']/collision/geometry/box").get('size'))
    assert urdf_body == pytest.approx(body)
    for link in ('base_link', 'front_left_wheel', 'front_left_knuckle', 'lidar_link'):
        sdf_mass = float(model.find(f"link[@name='{link}']/inertial/mass").text)
        urdf_mass = float(robot.find(f"link[@name='{link}']/inertial/mass").get('value'))
        assert urdf_mass == pytest.approx(sdf_mass)
