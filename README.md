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
  проверкой `publish_hz` (воспроизведение отказа, не для сдачи).

Отчёты: [evidence/pr01](evidence/pr01), [evidence/pr02](evidence/pr02),
[evidence/pr03](evidence/pr03), [evidence/pr04](evidence/pr04)
([команды и вывод](evidence/pr04/parameters.md)).
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

## ПР04: параметры ноды `patrol`

| Параметр | По умолчанию | Допустимо | Что меняет |
|---|---|---|---|
| `linear_speed` | 0.5 м/с | [0, 1], конечное | `linear.x` команды |
| `turn_rate` | 0.3 рад/с | [−1, 1], конечное | `angular.z` команды |
| `publish_hz` | 10.0 Гц | [1, 30], конечное | период таймера `1/publish_hz` |

- [patrol/control.py](src/patrol/patrol/control.py) — чистые функции
  `compute_command(pose, linear_speed, turn_rate)`, `check_parameter(name, value)`
  (причина отказа или `None`) и `timer_period(publish_hz)`.
- [patrol/patrol.py](src/patrol/patrol/patrol.py) — нода:
  - `add_on_set_parameters_callback` — **проверка до изменения**: при отказе
    rclpy не меняет значение, таймер и скорости не трогаются;
  - `add_post_set_parameters_callback` — **применение** принятых значений;
    для `publish_hz` старый таймер уничтожается, создаётся новый — одновременно
    всегда один таймер.
- Тесты: [test_control.py](src/patrol/test/test_control.py) (чистые функции:
  10→5 Гц, 0, отрицательное, NaN, границы) и
  [test_parameters_node.py](src/patrol/test/test_parameters_node.py)
  (настоящая нода: отказ сохраняет значение, объект таймера и период).

Параметры типа double: `ros2 param set /patrol publish_hz 5.0`. Целое `5`
отклоняет сам ROS по типу (`Wrong parameter type`), до проверки ноды.

## ПР04: сборка и тесты

```bash
source /opt/ros/lyrical/setup.bash
export ROS_DOMAIN_ID=16
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
(cd src/patrol && python3 -m pytest test -q)
```

Тесты запускаются из каталога пакета: сгенерированные линтеры (flake8, mypy)
проверяют текущий каталог и из корня захватывают копии в `build/`.

## ПР04: опыт

```bash
ros2 launch turtle_bringup sim.launch.py                                   # A
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel             # B
ros2 param set /patrol publish_hz 5.0                                      # C: принято
ros2 param set /patrol publish_hz 0.0                                      # C: отклонено
ros2 param get /patrol publish_hz                                          # C: 5.0
timeout --signal=INT 12s ros2 topic hz /turtle1/cmd_vel                    # C: ≈5 Гц
```

Отказ без проверки: `git switch pr04-defect`, пересобрать и повторить
`timeout 10s ros2 param set /patrol publish_hz 0.0` — нода падает с
`ZeroDivisionError` в `timer_period` (exit 1), поток команды прекращается,
а `ros2 param set` не получает ответа и завершается по таймауту.
Те же тесты на этой ветке падают (`test_invalid_publish_hz_rejected_state_kept`
и тесты `check_parameter` для `publish_hz`).

## Проверка

```bash
curl -fsSLo course-kit.tar.gz \
  https://ros.lms.ci.nsu.ru/downloads/robotics-course-kit-v1-w04-fec6b4e886c1.tar.gz
printf '%s  %s\n' fec6b4e886c19146078bf69fbf90a19279a4cd33f656642395350b299efeb226 \
  course-kit.tar.gz | sha256sum -c -
mkdir -p .course-kit && tar -xzf course-kit.tar.gz -C .course-kit
python3 .course-kit/v1/tools/check_practice.py PR04 --submission .
```

Сдача: коммит A — код, тесты, README, workflow; коммит B — только `evidence/pr04/`
и `AI_USAGE.md`. `report.commit` = SHA коммита A, сдаётся SHA коммита B.
