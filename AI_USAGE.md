# Использование ИИ

- ИИ (Qwen) использовался для:
  - адаптации команды `docker run` под WSL 2 с WSLg;
  - объяснения причины сбоя discovery в DDS при разных ROS_DOMAIN_ID.
  - Заполнение environment-sources.txt
  - настройка автотестов
- Все команды ROS и интерпретация результатов выполнены автором работы самостоятельно.
## PR02

- Использован ИИ: да
- Модель и версия: Claude Opus 5.5 (Anthropic)
- Среда или интерфейс агента: Claude Code (CLI) на Windows с доступом к WSL 2
  и Docker-контейнеру osrf/ros:lyrical-desktop-full
- Затронутые компоненты: пакет src/turtle_bringup (launch-файл, data_files
  в setup.py), README, .gitignore, workflow .github/workflows/pr02.yml,
  evidence/pr02 (commands.md, types.md, report.json), перевод репозитория
  на схему «ветка на практику» (pr01, pr02).
- Характер помощи: разбор задания и эталонного примера; подготовка пакета,
  launch-файла, README и CI; черновики commands.md и types.md и их
  оформление по фактическим выводам CLI.
- Как результат был проверен независимо: команды сборки и эксперимента
  выполнены автором в контейнере ROS 2 Lyrical, окно turtlesim наблюдалось
  через WSLg; таблицы и выводы в commands.md сверены с сохранёнными
  выводами ros2 CLI. Сборка, установка launch, py_compile, тесты пакета
  и check_practice.py PR02 выполнены локально.

Переписка и промпты не приложены.

## PR03

- Использован ИИ: да
- Модель и версия: Claude Opus 5.5 (Anthropic)
- Среда или интерфейс агента: Claude Code (CLI) на Windows с доступом к WSL 2
  и Docker-контейнеру osrf/ros:lyrical-desktop-full
- Затронутые компоненты: пакет src/patrol — нода patrol/patrol.py, чистая
  функция patrol/control.py, тесты test/test_control.py; README;
  workflow .github/workflows/pr03.yml; evidence/pr03 (demo.md, report.json).
- Характер помощи: разбор задания; код ноды (подписка, таймер, издатель
  в относительный cmd_vel), вынесение логики в чистую функцию и её тесты;
  исправление завершения по Ctrl+C (RCLError при штатном обработчике SIGINT
  rclpy); CI; черновик demo.md по фактическим выводам CLI.
- Как результат был проверен независимо: сборка, тесты пакета и опыт
  (запуск без remap и с remap, topic info, измерение частоты за 10 с,
  остановка по Ctrl+C) выполнены автором в контейнере ROS 2 Lyrical,
  окно turtlesim наблюдалось через WSLg; выводы в demo.md сверены
  с сохранёнными выводами ros2 CLI и pytest. check_practice.py PR03
  выполнен локально.

Переписка и промпты не приложены.

## PR04

- Использован ИИ: да
- Модель и версия: Claude Opus 5.5 (Anthropic)
- Среда или интерфейс агента: Claude Code (CLI) на Windows с доступом к WSL 2
  и Docker-контейнеру osrf/ros:lyrical-desktop-full
- Затронутые компоненты: пакет src/patrol — параметры и их проверка
  (patrol/control.py, patrol/patrol.py), тесты test/test_control.py
  и test/test_parameters_node.py; ветка pr04-defect с отключённой проверкой;
  README; workflow .github/workflows/pr04.yml; evidence/pr04 (parameters.md,
  report.json).
- Характер помощи: разбор задания; код параметров (проверка
  в on_set-callback, применение и пересоздание таймера в post_set-callback),
  чистая функция check_parameter и тесты; коммит с дефектом; CI;
  черновик parameters.md по фактическим выводам CLI.
- Как результат был проверен независимо: сборка, тесты на ветках pr04
  и pr04-defect и опыт (ros2 param set 5.0 / 0.0 / -5.0 / NaN, измерение
  частоты, изменение скорости, вызов /clear, ros2 action list, падение ноды
  на ветке с дефектом) выполнены автором в контейнере ROS 2 Lyrical; выводы
  в parameters.md сверены с сохранёнными выводами ros2 CLI и pytest.
  check_practice.py PR04 выполнен локально.

Переписка и промпты не приложены.
