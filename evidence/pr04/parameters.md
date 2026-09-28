# ПР04. Параметризуем движение: команды и вывод

Среда: Windows 10 + WSL 2 (Ubuntu 24.04), контейнер
`osrf/ros:lyrical-desktop-full` (ROS 2 Lyrical), репозиторий в `/work`,
`ROS_DOMAIN_ID=16`. Опыт: 2026-09-28, 13:24:54–13:31:40 UTC
([started-utc.txt](started-utc.txt), [finished-utc.txt](finished-utc.txt)).
Терминалы: A — `ros2 launch turtle_bringup sim.launch.py`,
B — `ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel`,
C — `ros2 param`, `ros2 topic`, `ros2 service`, `ros2 action`.
Окно turtlesim во время опыта не отобразилось (сбой вывода WSLg, позже
устранён перезапуском WSL), поэтому всё ниже подтверждено выводом CLI:
поза, параметры, частота и ответы сервиса.

`ros2 topic type /turtle1/pose` → `turtlesim_msgs/msg/Pose`
([pose-type.txt](pose-type.txt)).

## Как устроены параметры

| Параметр | По умолчанию | Допустимо | Что меняет |
|---|---|---|---|
| `linear_speed` | 0.5 м/с | [0, 1], конечное | `linear.x` команды |
| `turn_rate` | 0.3 рад/с | [−1, 1], конечное | `angular.z` команды |
| `publish_hz` | 10.0 Гц | [1, 30], конечное | период таймера `1/publish_hz` |

1. **Проверка до изменения** — `add_on_set_parameters_callback`. Callback
   вызывает чистую функцию `check_parameter(name, value)`; если она вернула
   причину, callback отвечает `SetParametersResult(successful=False, reason=...)`,
   и rclpy **не записывает** новое значение. Таймер, скорости и поток команды
   не трогаются.
2. **Применение после проверки** — `add_post_set_parameters_callback`.
   Скорости просто сохраняются; для `publish_hz` старый таймер уничтожается
   (`destroy_timer`) и создаётся новый с периодом `1/publish_hz`, поэтому
   одновременно работает ровно один таймер.
3. Диапазоны указаны только в описании параметра. `floating_point_range`
   в дескрипторе не используется: тогда rclpy отклонял бы значения сам,
   до кода ноды, и проверку нельзя было бы воспроизводимо отключить.

`ros2 param list /patrol` → `linear_speed`, `publish_hz`, `turn_rate`
и служебные параметры ([param-list.txt](param-list.txt));
`ros2 param describe` — тип `double` и описание с диапазоном
([param-describe.txt](param-describe.txt)).

## 1. Допустимое изменение 10 → 5 Гц

```text
$ ros2 param get /patrol publish_hz
Double value is: 10.0
$ timeout --signal=INT 12s ros2 topic hz /turtle1/cmd_vel
average rate: 10.000   min: 0.099s max: 0.101s   window: 99
$ ros2 param set /patrol publish_hz 5.0
Set parameter successful
$ ros2 param get /patrol publish_hz
Double value is: 5.0
$ timeout --signal=INT 12s ros2 topic hz /turtle1/cmd_vel
average rate: 5.000    min: 0.199s max: 0.201s   window: 42
```

Файлы: [param-get-initial.txt](param-get-initial.txt), [hz-10.txt](hz-10.txt),
[param-set-5.txt](param-set-5.txt), [param-get-after-5.txt](param-get-after-5.txt),
[hz-5.txt](hz-5.txt). В логе ноды — `publish_hz = 5.0` ([patrol.txt](patrol.txt)).
Интервал между командами изменился с 0.1 с на 0.2 с: таймер пересоздан.

## 2. Недопустимые значения отклонены, состояние сохранено

```text
$ ros2 param set /patrol publish_hz 0.0
Setting parameter failed: publish_hz=0.0: вне диапазона [1.0, 30.0]
$ ros2 param set /patrol publish_hz -5.0
Setting parameter failed: publish_hz=-5.0: вне диапазона [1.0, 30.0]
$ ros2 param set /patrol publish_hz .nan
Setting parameter failed: publish_hz=nan: нужно конечное число
$ ros2 param get /patrol publish_hz
Double value is: 5.0
$ timeout --signal=INT 12s ros2 topic hz /turtle1/cmd_vel
average rate: 5.000    min: 0.199s max: 0.201s   window: 49
```

Файлы: [param-set-0.txt](param-set-0.txt), [param-set-neg.txt](param-set-neg.txt),
[param-set-nan.txt](param-set-nan.txt),
[param-get-after-reject.txt](param-get-after-reject.txt),
[hz-after-reject.txt](hz-after-reject.txt). В логе ноды три строки
`WARN ... rejected publish_hz=...` ([patrol.txt](patrol.txt)).
Значение осталось 5.0, поток — 5 Гц: активное состояние не разрушено.

Замечание: `ros2 param set /patrol publish_hz 5` (целое) отклоняет уже сам
ROS по типу (`Wrong parameter type`), до кода ноды, — значения передаются
как double (`5.0`).

## 3. Скорости

```text
$ ros2 param set /patrol linear_speed 1.0
Set parameter successful
$ ros2 topic echo /turtle1/cmd_vel --once
linear: {x: 1.0, y: 0.0, z: 0.0}
angular: {x: 0.0, y: 0.0, z: 0.3}
```

([param-set-speed.txt](param-set-speed.txt), [cmd-after-speed.txt](cmd-after-speed.txt)).
Следующая же команда таймера несёт новую скорость; `turn_rate` не изменился.

## 4. Отказ: проверка частоты отключена (ветка `pr04-defect`)

Коммит `3f307f8` поверх реализации ([defect-commit.txt](defect-commit.txt)),
вся разница — две строки ([defect-diff.txt](defect-diff.txt)):

```diff
 def check_parameter(name: str, value: object) -> Optional[str]:
+    if name == 'publish_hz':
+        return None  # ДЕФЕКТ ПР04: проверка частоты временно отключена
```

**Те же тесты** на этой ветке: `14 failed, 27 passed, 1 skipped`
([tests-defect.txt](tests-defect.txt)) — в том числе
`test_invalid_publish_hz_rejected_state_kept[0.0]`, `[-5.0]`, `[nan]`
и тесты `check_parameter` для `publish_hz`. Для `-5.0` нода падает уже в rcl:
`RCLError: failed to create timer: timer period must be non-negative`.

Нода с дефектом (B) и `publish_hz 0.0` (C):

```text
$ timeout 10s ros2 param set /patrol publish_hz 0.0
param set exit=124
$ ros2 node list --no-daemon --spin-time 2
/turtlesim
```

Лог ноды ([patrol-defect.txt](patrol-defect.txt)), сокращённо:

```text
  File ".../rclpy/node.py", line 1038, in _call_post_set_parameters_callback
  File "/work/build/patrol/patrol/patrol.py", line 87, in _apply_parameters
    self._restart_timer(param.value)
  File "/work/build/patrol/patrol/patrol.py", line 95, in _restart_timer
    self._timer = self.create_timer(timer_period(publish_hz), self._on_timer)
  File "/work/build/patrol/patrol/control.py", line 68, in timer_period
    return 1.0 / publish_hz
ZeroDivisionError: division by zero
[ros2run]: Process exited with failure 1
```

**Причина.** Без проверки rclpy принимает 0.0 и записывает его в параметр,
затем post-callback вызывает `_restart_timer`: старый таймер уже уничтожен,
а `1.0 / 0.0` бросает `ZeroDivisionError`. Исключение выходит из сервиса
параметров через `spin`, нода завершается с кодом 1: поток команд
прекращается, черепаха останавливается, клиент `ros2 param set` так и не
получает ответа и завершается по `timeout` (124), в графе остаётся только
`/turtlesim` ([param-set-0-defect.txt](param-set-0-defect.txt),
[nodes-after-defect.txt](nodes-after-defect.txt)).

## 5. Исправление подтверждено тем же тестом

После возврата на ветку `pr04` (проверка включена) те же тесты:
**41 passed, 1 skipped** ([tests.txt](tests.txt)). Ключевой тест
`test_invalid_publish_hz_rejected_state_kept` для 0.0, −5.0 и NaN проверяет
на настоящей ноде, что `set_parameters` вернул `successful=False`,
значение осталось 10.0, **тот же объект таймера** работает с периодом
0.1 с и таймер один. Тест `test_publish_hz_10_to_5_recreates_single_timer`
проверяет обратное: 5.0 принято, период 0.2 с, таймер новый и единственный.
Чистая функция покрыта `test_control.py`: 10→5, 0, отрицательное, NaN, inf,
границы диапазонов и нечисловые значения. Сборка — [build.txt](build.txt).

## 6. Сервис и экшен

```text
$ ros2 service call /clear std_srvs/srv/Empty
requester: making request: std_srvs.srv.Empty_Request()
response:
std_srvs.srv.Empty_Response()
$ ros2 action list -t
/turtle1/rotate_absolute [turtlesim_msgs/action/RotateAbsolute]
```

([clear.txt](clear.txt), [action-list.txt](action-list.txt))

**Запрос и цель.** Запрос сервиса (`/clear`) — это разовый вызов: клиент
отправляет запрос и ждёт один ответ, прогресса и отмены нет.
Цель экшена (`/turtle1/rotate_absolute`) запускает длительное выполнение:
сервер принимает её, во время работы присылает обратную связь (оставшийся
угол), в конце — результат, и цель можно отменить до завершения.
