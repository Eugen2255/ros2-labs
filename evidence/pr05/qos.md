# ПР05. Launch, QoS и повтор записи

Среда: Windows 10 + WSL 2 (Ubuntu 24.04), контейнер
`osrf/ros:lyrical-desktop-full` (ROS 2 Lyrical), репозиторий в `/work`,
`ROS_DOMAIN_ID=16`. Опыт: 2026-10-23, 06:57:03–07:00:38 UTC
([started-utc.txt](started-utc.txt), [finished-utc.txt](finished-utc.txt)).
Терминалы: A — `ros2 launch`, B — `ros2 bag play`, C — диагностика.

## 1. Сборка и тесты

`colcon build` трёх пакетов ([build.txt](build.txt)), `colcon test` +
`colcon test-result --all --verbose`: **54 tests, 0 errors, 0 failures,
2 skipped** ([tests.txt](tests.txt); пропущены только copyright-проверки).
В их числе launch-тест `course_bringup/test/test_patrol_launch.py`: система
поднимается в `/robot_t` (домен 87, turtlesim offscreen), проверяются имена
нод, remap команды, QoS издателя, то, что `best_effort`-подписчик получает
поток, а `reliable` — нет, и что после остановки все процессы вернули код 0.

## 2. Система одной командой, имена

```text
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=reliable record:=true
[INFO] [launch.user]: namespace=/robot_a subscriber_reliability=reliable record=true bag_dir=evidence/pr05/bag
```

`ros2 node list` ([nodes.txt](nodes.txt)):

```text
/robot_a/patrol
/robot_a/pose_listener
/robot_a/pose_relay
/rosbag2_recorder
/turtlesim
```

- Ноды робота получили пространство имён из `PushRosNamespace` внутри
  `GroupAction`; turtlesim и запись вне группы — глобальные.
- `ros2 topic list -t` ([topics.txt](topics.txt)): `/robot_a/sensor_pose`
  (относительное `sensor_pose` у `pose_relay`), `/turtle1/cmd_vel`,
  `/turtle1/pose`. Топика `/robot_a/cmd_vel` нет: относительный выход `cmd_vel`
  у `patrol` переназначен в `/turtle1/cmd_vel`, иначе команда ушла бы
  в пространство имён робота, которое turtlesim не слушает (как в ПР03).
  Лог `patrol`: `publishing to /turtle1/cmd_vel`, `first pose: x=5.544` —
  черепаха едет.

## 3. Сбой: reliable-подписчик и best_effort-датчик

`ros2 topic info -v /robot_a/sensor_pose` ([topic-info-reliable.txt](topic-info-reliable.txt)):

| Конечная точка | Нода | Reliability |
|---|---|---|
| издатель | `/robot_a/pose_relay` | **BEST_EFFORT** |
| подписчик | `/robot_a/pose_listener` | **RELIABLE** |
| подписчик | `/rosbag2_recorder` | BEST_EFFORT |

Лог launch ([launch-reliable.txt](launch-reliable.txt)):

```text
[robot_a.pose_listener]: incompatible QoS with a publisher on /robot_a/sensor_pose: RELIABILITY (requested reliable); messages will not be delivered
[robot_a.pose_relay]: New subscription discovered on topic 'sensor_pose', requesting incompatible QoS. No messages will be sent to it. Last incompatible policy: RELIABILITY
[robot_a.pose_listener]: received 0 messages in 2 s (total 0, reliable)     ← 21 раз подряд
```

Echo с `reliable` ([qos-before.txt](qos-before.txt)): предупреждение
`offering incompatible QoS … Last incompatible policy: RELIABILITY`, сообщений
нет, `exit=124` (остановлен `timeout`). Топик виден, издатель есть,
подписчик есть — а доставки нет.

**Причина.** В DDS подписчик *запрашивает* QoS, издатель *предлагает*, и пара
соединяется, только если предложение не слабее запроса. `RELIABLE` требует
подтверждений и повторной отправки потерянного; издатель `BEST_EFFORT` этого не
делает, поэтому запрос не выполним и пара не создаётся — ни одного сообщения,
хотя имя и тип совпадают. Обратное сочетание (`RELIABLE` издатель,
`BEST_EFFORT` подписчик) совместимо. Запись при этом шла: `rosbag2_recorder`
подписался как `BEST_EFFORT` — он подстраивает QoS под издателя.

## 4. Исправление на живом потоке

```text
ros2 launch course_bringup patrol.launch.py namespace:=robot_a subscriber_reliability:=best_effort
```

- `topic info -v`: издатель `BEST_EFFORT`, подписчик `pose_listener`
  **`BEST_EFFORT`** ([topic-info-best-effort.txt](topic-info-best-effort.txt)).
- Лог: `received 127 / 125 / 125 messages in 2 s (… best_effort)`
  ([launch-best-effort.txt](launch-best-effort.txt)) — ≈62 Гц, весь поток позы.
- Echo с `best_effort` получил позу x=4.429482, y=8.453503,
  `linear_velocity: 0.5`, `exit=0` ([qos-after.txt](qos-after.txt)).

Код не менялся — только аргумент launch `subscriber_reliability`.

## 5. Запись и воспроизведение

Запись — первый запуск с `record:=true`
(`ros2 bag record -s mcap -o evidence/pr05/bag --topics /robot_a/sensor_pose`
через `IfCondition`): **42.6 с, 2818 сообщений** `turtlesim_msgs/msg/Pose`, MCAP,
200 КиБ ([bag-metadata.yaml](bag-metadata.yaml), `ros2 bag info` — в конце
[qos-after.txt](qos-after.txt)). По Ctrl+C `Recording stopped`, все пять
процессов `process has finished cleanly`.

Перед воспроизведением живая система остановлена: `ros2 node list` пуст
([nodes-after-stop.txt](nodes-after-stop.txt)). Затем

```text
ros2 bag play evidence/pr05/bag --qos-profile-overrides-path config/qos-overrides.yaml --loop
```

- `topic info -v`: единственный издатель — **`rosbag2_player`**, `BEST_EFFORT`
  ([topic-info-replay.txt](topic-info-replay.txt)). Значит, всё, что получают
  подписчики, — из записи, а не из живой системы.
- `reliable` echo: та же несовместимость, `exit=124` ([qos-before.txt](qos-before.txt)).
- `best_effort` echo: x=5.400633, y=5.550314, `linear_velocity: 0.5`,
  `exit=0` ([qos-after.txt](qos-after.txt)).

Одна и та же запись воспроизводит и отказ, и доставку — разница только
в QoS подписчика. [config/qos-overrides.yaml](../../config/qos-overrides.yaml)
задаёт издателю при воспроизведении явно `best_effort`, keep_last, depth 10 —
как у живого `pose_relay`, а не полагается на профиль из метаданных записи.

### Сверка значений с записью

[replay_check.py](replay_check.py) читает MCAP и ищет позы из echo
([replay-check.txt](replay-check.txt)): поза с воспроизведения — сообщение
№1281 из 2818. Но и поза с **живого** потока (снята после окончания записи)
нашлась в записи — №796. Причина: turtlesim интегрирует движение с
фиксированным шагом 16 мс, а `patrol` каждый запуск ведёт черепаху из той же
точки с теми же скоростями, поэтому последовательность поз повторяется
бит в бит. Значит, **по значениям нельзя различить живое и записанное
сообщение** — источник при воспроизведении доказывает граф (только
`rosbag2_player`, живых нод нет). Поэтому живую систему и останавливали
перед `bag play`: иначе входные сообщения «до» и «после» смешались бы
незаметно.

## 6. Завершение процессов

Во всех запусках по Ctrl+C каждая нода и запись завершились с
`process has finished cleanly` ([launch-reliable.txt](launch-reliable.txt),
[launch-best-effort.txt](launch-best-effort.txt)). Для этого общий
`patrol/runner.py` крутит `spin_once` с таймаутом 0,1 с: обработчик Ctrl+C
в Python выполняется только между инструкциями Python, а бесконечный
`rclpy.spin` ждёт событий в C-коде — `pose_relay` (без таймера) после
остановки turtlesim не получал бы событий и не реагировал на Ctrl+C.
