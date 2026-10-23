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
  запись MCAP и проверка на воспроизведении.

Отчёты: [evidence/pr01](evidence/pr01) … [evidence/pr05](evidence/pr05)
([QoS: до](evidence/pr05/qos-before.txt), [после](evidence/pr05/qos-after.txt)).
[Декларация помощи ИИ](AI_USAGE.md), CI: [.github/workflows](.github/workflows).
Инструкции к прошлым ПР — в README соответствующих веток.

## Среда

Windows 10 + WSL 2 (Ubuntu 24.04) и контейнер `osrf/ros:lyrical-desktop-full`
(ROS 2 Lyrical). Окно turtlesim выводится через WSLg. Домен — `ROS_DOMAIN_ID=16`
во всех терминалах.

```bash
docker run -d --name pr01-student-demo \
  -e DISPLAY -e WAYLAND_DISPLAY -e XDG_RUNTIME_DIR=/mnt/wslg/runtime-dir \
  -v /tmp/.X11-unix:/tmp/.X11-unix -v /mnt/wslg:/mnt/wslg \
  -v "$PWD":/work -w /work \
  osrf/ros:lyrical-desktop-full sleep infinity
docker exec -it pr01-student-demo bash
```

## ПР05: система одной командой

```text
turtlesim ── /turtle1/pose ──┬──▶ /robot_a/patrol ── /turtle1/cmd_vel ──▶ turtlesim
(глобальный)  (≈62 Гц)       │                      (remap cmd_vel)
                             └──▶ /robot_a/pose_relay ── /robot_a/sensor_pose (best_effort)
                                                            ├──▶ /robot_a/pose_listener (QoS из аргумента)
                                                            └──▶ rosbag2_recorder → MCAP (record:=true)
```

- [course_bringup/launch/patrol.launch.py](src/course_bringup/launch/patrol.launch.py):
  - turtlesim подключается из `turtle_bringup/sim.launch.py` и остаётся
    в глобальном пространстве имён;
  - `patrol`, `pose_relay`, `pose_listener` — в `GroupAction` с
    `PushRosNamespace(namespace)`; выход `cmd_vel` у `patrol` переназначен
    в `/turtle1/cmd_vel`;
  - `ros2 bag record -s mcap` запускается только при `record:=true`
    через `IfCondition`.

| Аргумент | По умолчанию | Значение |
|---|---|---|
| `namespace` | `robot_a` | пространство имён нод робота |
| `record` | `false` | `true` — записать `/<namespace>/sensor_pose` в MCAP |
| `bag_dir` | `evidence/pr05/bag` | каталог записи (не должен существовать) |
| `subscriber_reliability` | `best_effort` | `reliable` воспроизводит несовместимость QoS |

- [patrol/pose_relay.py](src/patrol/patrol/pose_relay.py) — пересылает
  `/turtle1/pose` в относительный `sensor_pose` с QoS `best_effort`, depth 10.
- [patrol/pose_listener.py](src/patrol/patrol/pose_listener.py) — подписчик
  `sensor_pose` с надёжностью из параметра `reliability`; раз в 2 с пишет
  в лог число полученных сообщений, при несовместимом QoS — предупреждение.
- [patrol/qos.py](src/patrol/patrol/qos.py) — профиль `sensor_qos(reliability)`.
- [patrol/runner.py](src/patrol/patrol/runner.py) — общий `main` всех нод:
  `spin_once` с таймаутом 0,1 с, чтобы Ctrl+C срабатывал и у ноды без таймера.
- [config/qos-overrides.yaml](config/qos-overrides.yaml) — QoS издателя
  при воспроизведении записи.

### Почему reliable-подписчик не получает данных

Издатель `best_effort` не подтверждает доставку и не повторяет потерянное.
Подписчик `reliable` требует именно этого, а DDS соединяет пару, только если
предложенный издателем QoS не слабее запрошенного. Поэтому топик виден
в графе, но пара не создаётся (`incompatible QoS … RELIABILITY`).
Обратное сочетание — `reliable` издатель и `best_effort` подписчик — совместимо.

## ПР05: сборка и тесты

```bash
source /opt/ros/lyrical/setup.bash
export ROS_DOMAIN_ID=16
colcon build --symlink-install --packages-select turtle_bringup patrol course_bringup
source install/setup.bash
colcon test --packages-select patrol course_bringup
colcon test-result --all --verbose
```

[test_patrol_launch.py](src/course_bringup/test/test_patrol_launch.py) —
launch-тест (домен 87, turtlesim offscreen): ноды в `/robot_t`, turtlesim
глобальный, команда `patrol` идёт в `/turtle1/cmd_vel`, издатель `sensor_pose`
— `best_effort`, `best_effort`-подписчик получает поток, а `reliable` — нет;
после остановки все процессы завершились с кодом 0.

## ПР05: опыт

```bash
# сбой + запись
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=reliable record:=true
timeout 3s ros2 topic echo /robot_a/sensor_pose --qos-reliability reliable --once
# исправление
ros2 launch course_bringup patrol.launch.py subscriber_reliability:=best_effort
timeout 3s ros2 topic echo /robot_a/sensor_pose --qos-reliability best_effort --once
# воспроизведение (живая система остановлена)
ros2 bag play evidence/pr05/bag --qos-profile-overrides-path config/qos-overrides.yaml --loop
ros2 bag info evidence/pr05/bag
```

## Проверка

```bash
curl -fsSLo course-kit.tar.gz \
  https://ros.lms.ci.nsu.ru/downloads/robotics-course-kit-v1-w07-9b7fdd5424d3.tar.gz
printf '%s  %s\n' 9b7fdd5424d3d97e47d51dbe23064934585e62135dc2902844dd679529bda929 \
  course-kit.tar.gz | sha256sum -c -
mkdir -p .course-kit && tar -xzf course-kit.tar.gz -C .course-kit
python3 .course-kit/v1/tools/check_practice.py PR05 --submission .
```

Сдача: коммит A — код, тесты, launch, README, workflow; коммит B — только
`evidence/pr05/` и `AI_USAGE.md`. `report.commit` = SHA коммита A,
сдаётся SHA коммита B.
