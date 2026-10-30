# Практики по ROS 2

Корень репозитория — одновременно корень colcon workspace.
Каждая практика выполняется в своей ветке, следующая продолжает предыдущую:

- `pr01` — ПР01 (граф turtlesim, ROS_DOMAIN_ID), `master` указывает на тот же снимок;
- `pr02` — ПР02: пакет `turtle_bringup`, launch turtlesim, управление из CLI
  и диагностика неверного имени топика;
- `pr03` — ПР03: первая нода `patrol` — подписка на позу, таймер 10 Гц,
  публикация `Twist` в относительный `cmd_vel` и исправление через remap;
- `pr04` — ПР04: параметры `linear_speed`, `turn_rate`, `publish_hz`,
  проверка значений и пересоздание таймера;
- `pr04-defect` — один коммит поверх реализации ПР04 с временно отключённой
  проверкой `publish_hz` (воспроизведение отказа, не для сдачи);
- `pr05` — ПР05: launch всей системы в пространстве имён, QoS сенсорного потока,
  запись MCAP и проверка на воспроизведении;
- `pr06` — ПР06: URDF/Xacro-модель Ackermann-робота, дерево tf2, QoS `/tf_static`;
- `pr06-defect` — один коммит поверх реализации ПР06: `lidar_link` подвешен
  к `camera_link` вместо `base_link` (воспроизведение отказа, не для сдачи).

Отчёты: [evidence/pr01](evidence/pr01) … [evidence/pr06](evidence/pr06)
([системы координат](evidence/pr06/frames.md), [QoS tf](evidence/pr06/tf-qos.txt)).
[Декларация помощи ИИ](AI_USAGE.md), CI: [.github/workflows](.github/workflows).
Инструкции к прошлым ПР — в README соответствующих веток.

## Среда

Windows 10 + WSL 2 (Ubuntu 24.04) и контейнер `osrf/ros:lyrical-desktop-full`
(ROS 2 Lyrical, образ `sha256:e6b1cb530b65…`). Окна turtlesim и RViz выводятся
через WSLg. Домен — `ROS_DOMAIN_ID=16` во всех терминалах.

```bash
docker run -d --name pr01-student-demo \
  -e DISPLAY=:0 -e WAYLAND_DISPLAY=wayland-0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix -v /mnt/wslg:/mnt/wslg \
  -v "$PWD":/work -w /work \
  osrf/ros:lyrical-desktop-full sleep infinity
docker exec -it -u 1000:1000 -e HOME=/tmp/h pr01-student-demo bash
```

## ПР06: модель робота

Пакет [course_description](src/course_description):

- [urdf/vehicle.urdf.xacro](src/course_description/urdf/vehicle.urdf.xacro) —
  модель. Размеры — Xacro-переменные, взятые из
  `.course-kit/v1/models/course_ackermann/model.sdf` (плагины Gazebo не переносятся);
  СИ, оси по REP-103; инерция считается макросами `box_inertial` и
  `cylinder_inertial` из тех же размеров; `visual` и `collision` заданы отдельно.
- [launch/display.launch.py](src/course_description/launch/display.launch.py) —
  `robot_state_publisher` с `robot_description` из `xacro`, RViz и
  (по желанию) нулевые `joint_states`.
- [rviz/vehicle.rviz](src/course_description/rviz/vehicle.rviz) — Fixed Frame
  `base_link`, RobotModel из `/robot_description`, TF с подписями.

| Параметр Xacro | Значение | Источник в SDF |
|---|---|---|
| `wheelbase` | 0.80 м | `wheel_base` плагина, x колёс ±0.40 |
| `track` | 0.62 м | `wheel_separation`, y колёс ±0.31 |
| `wheel_radius`, `wheel_width` | 0.12 м, 0.07 м | цилиндр колеса |
| `body_length × width × height` | 1.05 × 0.52 × 0.22 м, центр на z = 0.12 | `body_collision` |
| `sensor_x`, `sensor_z` | 0.28 м, 0.38 м | позы `camera_link`, `lidar_link`, `imu_link` |
| массы | корпус 12, колесо 0.8, кулак 0.2, сенсор 0.0333 кг | `inertial/mass` |

```text
base_link ─┬─ front_left_steering_joint (revolute z)  → front_left_knuckle  ─ front_left_wheel_joint (continuous y)  → front_left_wheel
           ├─ front_right_steering_joint (revolute z) → front_right_knuckle ─ front_right_wheel_joint (continuous y) → front_right_wheel
           ├─ rear_left_wheel_joint (continuous y)    → rear_left_wheel
           ├─ rear_right_wheel_joint (continuous y)   → rear_right_wheel
           ├─ camera_joint (fixed, 0.28 0 0.38)       → camera_link
           ├─ lidar_joint  (fixed, 0.28 0 0.38)       → lidar_link
           └─ imu_joint    (fixed, 0.28 0 0.38)       → imu_link
```

Фиксированные звенья `robot_state_publisher` публикует в `/tf_static` сразу.
Кулаки и колёса попадают в `/tf`, только если кто-то публикует `joint_states`:
`joint_states:=true` запускает ноду `zero_joint_states` с нулевыми углами.

## ПР06: сборка, проверка, запуск

```bash
source /opt/ros/lyrical/setup.bash
export ROS_DOMAIN_ID=16
colcon build --symlink-install --packages-select course_description
source install/setup.bash
xacro src/course_description/urdf/vehicle.urdf.xacro > /tmp/vehicle.urdf
check_urdf /tmp/vehicle.urdf
colcon test --packages-select course_description
colcon test-result --test-result-base build/course_description --verbose
ros2 launch course_description display.launch.py                   # RViz
ros2 launch course_description display.launch.py joint_states:=true  # с колёсами
ros2 run tf2_ros tf2_echo base_link lidar_link
ros2 run tf2_tools view_frames
```

Тесты:

- [test_vehicle_model.py](src/course_description/test/test_vehicle_model.py) —
  один корень `base_link`, нет циклов, **ожидаемый parent каждого звена**,
  положения сенсоров в `base_link`, база/колея/радиус, типы и оси сочленений,
  отдельные `visual`/`collision`, физически возможная инерция, правдоподобные
  единицы СИ, `check_urdf`, совпадение размеров и масс с `model.sdf` из kit.
- [test_tf_static_launch.py](src/course_description/test/test_tf_static_launch.py) —
  launch-тест (домен 88): единственный издатель `/tf_static` —
  `robot_state_publisher`, `RELIABLE` + `TRANSIENT_LOCAL`; поздний подписчик
  `transient_local` получает три сенсорных фрейма от `base_link`, `volatile` —
  ничего; `tf2` даёт `base_link → lidar_link` = (0.28, 0, 0.38); процессы
  завершаются с кодом 0.

`robot_state_publisher` предупреждает: `root link base_link has an inertia …
KDL does not support`. Для tf это не важно (KDL игнорирует инерцию корня);
корнем по контракту курса остаётся `base_link`, как в `model.sdf`.

## Проверка отчёта

```bash
curl -fsSLo course-kit.tar.gz \
  https://ros.lms.ci.nsu.ru/downloads/robotics-course-kit-v1-w08-aea8efd0a516.tar.gz
printf '%s  %s\n' aea8efd0a51668af63f2e475b82bfa28bd76c21f20d8afea6b136d43a56a88fb \
  course-kit.tar.gz | sha256sum -c -
mkdir -p .course-kit && tar -xzf course-kit.tar.gz -C .course-kit
python3 .course-kit/v1/tools/check_practice.py PR06 --submission .
```

Сдача: коммит A — модель, launch, тесты, README, workflow; коммит B — только
`evidence/pr06/` и `AI_USAGE.md`. `report.commit` = SHA коммита A,
сдаётся SHA коммита B.
