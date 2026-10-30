# ПР06. Системы координат модели и их владельцы

Среда: Windows 10 + WSL 2 (Ubuntu 24.04), контейнер
`osrf/ros:lyrical-desktop-full` (ROS 2 Lyrical), `ROS_DOMAIN_ID=16`.
Опыт: 2026-10-30, 16:18:47–16:28:38 UTC ([started-utc.txt](started-utc.txt),
[finished-utc.txt](finished-utc.txt)). Модель —
[vehicle.urdf.xacro](../../src/course_description/urdf/vehicle.urdf.xacro),
запуск — `ros2 launch course_description display.launch.py`.

Единицы СИ (м, кг, рад), оси REP-103: x вперёд, y влево, z вверх.
`base_link` — центр между осями на высоте осей колёс, корень дерева.

## Связи дерева

Все положения — при нулевых углах сочленений, в родительском звене.

| Родитель → ребёнок | Сочленение, тип | Ожидаемое преобразование (xyz, м; rpy, рад) | Канал | Владелец публикации |
|---|---|---|---|---|
| `base_link` → `camera_link` | `camera_joint`, fixed | (0.28, 0, 0.38), (0, 0, 0) | `/tf_static` | `robot_state_publisher` |
| `base_link` → `lidar_link` | `lidar_joint`, fixed | (0.28, 0, 0.38), (0, 0, 0) | `/tf_static` | `robot_state_publisher` |
| `base_link` → `imu_link` | `imu_joint`, fixed | (0.28, 0, 0.38), (0, 0, 0) | `/tf_static` | `robot_state_publisher` |
| `base_link` → `front_left_knuckle` | `front_left_steering_joint`, revolute z, ±0.55 | (0.40, 0.31, 0) + поворот руля вокруг z | `/tf` | `robot_state_publisher` (угол — из `/joint_states`) |
| `base_link` → `front_right_knuckle` | `front_right_steering_joint`, revolute z, ±0.55 | (0.40, −0.31, 0) + поворот руля вокруг z | `/tf` | `robot_state_publisher` |
| `front_left_knuckle` → `front_left_wheel` | `front_left_wheel_joint`, continuous y | (0, 0, 0) + вращение колеса вокруг y | `/tf` | `robot_state_publisher` |
| `front_right_knuckle` → `front_right_wheel` | `front_right_wheel_joint`, continuous y | (0, 0, 0) + вращение колеса вокруг y | `/tf` | `robot_state_publisher` |
| `base_link` → `rear_left_wheel` | `rear_left_wheel_joint`, continuous y | (−0.40, 0.31, 0) + вращение вокруг y | `/tf` | `robot_state_publisher` |
| `base_link` → `rear_right_wheel` | `rear_right_wheel_joint`, continuous y | (−0.40, −0.31, 0) + вращение вокруг y | `/tf` | `robot_state_publisher` |

- База 0.80 м (x колёс ±0.40), колея 0.62 м (y ±0.31), радиус колеса 0.12 м —
  Xacro-переменные `wheelbase`, `track`, `wheel_radius`, взятые из
  `model.sdf` курса; совпадение проверяет `test_dimensions_match_course_sdf`.
- Камера, лидар и IMU в `model.sdf` стоят в одной точке (0.28, 0, 0.38) —
  модель повторяет контракт, а не «раздвигает» сенсоры.
- Оптического фрейма камеры (`camera_optical_frame`, z вперёд) нет: по
  контракту симулятор подписывает изображения `camera_link`.

**Владелец** каждого преобразования один — `robot_state_publisher`:
`ros2 topic info /tf_static --verbose` и `/tf --verbose` показывают
`Publisher count: 1`, `Node name: robot_state_publisher` ([tf-qos.txt](tf-qos.txt)).
Нода `zero_joint_states` (`joint_states:=true`) публикует только **углы**
в `/joint_states`; преобразования по ним считает тот же
`robot_state_publisher`. `view_frames` пишет `Broadcaster: default_authority`
— это поле authority сообщения, а не имя ноды; владельца показывает
`topic info`.

Не публикуются в этой работе: `map` и `odom` (REP-105). По контракту курса
`odom → base_link` в `/tf` будет единственным владельцем у адаптера
одометрии (ПР07), не у `robot_state_publisher`, — иначе у одной связи
стало бы два издателя.

## Что показали инструменты

- `xacro` + `check_urdf`: `root Link: base_link has 7 child(ren)`, дерево из
  10 звеньев, `exit=0` ([model-check.txt](model-check.txt)).
- RViz (Fixed Frame `base_link`): корпус, жёлтая метка спереди, сенсоры;
  без `joint_states` колёс нет и RobotModel сообщает об отсутствии их
  преобразований — это ожидаемо ([launch.txt](launch.txt)). С
  `joint_states:=true` колёса появляются ([launch-joint-states.txt](launch-joint-states.txt)).
- `view_frames` без `joint_states`: только `base_link → camera_link / imu_link /
  lidar_link`, `Average rate: 10000.0`, `Most recent transform: 0.0` —
  так `view_frames` помечает статические связи ([view-frames.pdf](view-frames.pdf)).
  С `joint_states:=true` добавляются кулаки и колёса с частотой ≈10.2 Гц
  — частотой `/joint_states` ([view-frames-full.pdf](view-frames-full.pdf)).
- `tf2_echo base_link lidar_link` → `Translation: [0.280, 0.000, 0.380]`,
  поворот единичный ([tf2-echo-lidar.txt](tf2-echo-lidar.txt));
  `tf2_echo base_link front_left_wheel` → `[0.400, 0.310, 0.000]`
  ([tf2-echo-wheel.txt](tf2-echo-wheel.txt)). Первая строка
  `Waiting for transform … frame does not exist` — `tf2_echo` стартует
  раньше, чем получил `/tf_static`; через мгновение преобразование есть.
- `ros2 topic echo /tf_static --once`: три связи, у всех `frame_id: base_link`
  ([tf-static-echo.txt](tf-static-echo.txt)).
- Тесты: **23 tests, 0 failures, 1 skipped** ([tests.txt](tests.txt)).

`robot_state_publisher` предупреждает `root link base_link has an inertia …
KDL does not support`: KDL игнорирует инерцию корня, на tf это не влияет;
корнем по контракту остаётся `base_link`, как в `model.sdf`.
RViz пишет `Could not load pixmap …svg`: в образе нет Qt-плагина SVG
(`qt6-svg-plugins`), поэтому не грузятся иконки; 3D-вид не затронут.

## Дефект: неверный parent у лидара (ветка `pr06-defect`)

Коммит `38060d5` ([defect-commit.txt](defect-commit.txt)), вся разница
([defect-diff.txt](defect-diff.txt)):

```diff
-  <xacro:sensor_joint name="lidar"/>
+  <xacro:sensor_joint name="lidar" parent="camera_link"/>
```

Offset (0.28, 0, 0.38) сохранён, но теперь он отсчитывается от камеры.

| Проверка | `pr06` | `pr06-defect` |
|---|---|---|
| `check_urdf` | `exit=0`, `base_link` 7 детей | **`exit=0`**, `base_link` 6 детей, `camera_link → lidar_link` ([model-check-defect.txt](model-check-defect.txt)) |
| `/tf_static`, связь лидара | `frame_id: base_link` | `frame_id: camera_link` ([tf-static-defect.txt](tf-static-defect.txt)) |
| `tf2_echo base_link lidar_link` | [0.280, 0.000, 0.380] | **[0.560, 0.000, 0.760]** ([tf2-echo-lidar-defect.txt](tf2-echo-lidar-defect.txt)) |
| `colcon test` | 23 tests, 0 failures | **4 failures** ([tests-defect.txt](tests-defect.txt)) |

Упавшие тесты: `test_expected_parent_of_every_link`,
`test_sensor_pose_in_base_link[lidar_link]`, `test_dimensions_match_course_sdf`
и launch-тест (`test_late_transient_local_subscriber_gets_sensor_frames`,
`test_tf2_lookup_base_link_to_lidar`).

**Почему так.** Положение звена в `base_link` — произведение преобразований
по цепочке родителей. При parent `camera_link` к offset лидара добавляется
offset камеры: (0.28, 0, 0.38) + (0.28, 0, 0.38) = (0.56, 0, 0.76) — лидар
«висит» в 0.28 м впереди и 0.38 м выше настоящего места, и каждое его
измерение будет пересчитано в `base_link` с этой ошибкой. Для `check_urdf`
дерево по-прежнему корректно: один корень, нет циклов, все ссылки разрешены.
**Структурная корректность не доказывает геометрию** — смысл связей
проверяет тест ожидаемого parent и положения сенсора.

**Исправление.** Возврат на `pr06` (`parent` по умолчанию `base_link`) и тот же
тест: **23 tests, 0 failures** ([tests-after.txt](tests-after.txt)),
`tf2_echo base_link lidar_link` → [0.280, 0.000, 0.380]
([tf2-echo-lidar-after.txt](tf2-echo-lidar-after.txt)).
