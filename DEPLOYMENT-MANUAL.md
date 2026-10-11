# OJS с нуля своими руками

Инструкция для нашего случая: macOS, Docker с Colima, локальный тестовый журнал.
Ты сам создаёшь папку, конфигурацию, запускаешь контейнеры и устанавливаешь OJS
в браузере. Готовые файлы проекта копировать не нужно.

«С нуля» здесь означает новый стенд с пустой базой и собственной конфигурацией.
OJS берём из готового Docker-образа: собирать PHP и веб-сервер из исходников для
этого прогона не требуется. Docker и Colima на твоём компьютере уже установлены.

## Что мы собираем

В одном Docker-проекте будут три контейнера:

| Контейнер | Что делает | Как к нему обращаемся |
| --- | --- | --- |
| `ojs` | Apache и PHP запускают OJS | Браузер: `http://localhost:8080` |
| `db` | MariaDB хранит пользователей, настройки и данные статей | OJS обращается к `db` внутри Docker |
| `mailpit` | Принимает тестовые письма вместо настоящей отправки | SMTP внутри Docker: `mailpit:1025`; браузер: `http://localhost:8025` |

Рукописи хранятся в файлах, а их описания и связи — в базе.
Поэтому сохранить только базу для полного восстановления журнала недостаточно.

## Шаг 1. Убедиться, что Docker работает

В терминале:

```bash
colima start
docker context use colima
docker info
```

Colima запускает Linux-виртуальную машину. В ней работает Docker Engine.
Команда `docker` на macOS обращается к этому серверу.

**Проверка:** в выводе `docker info` есть раздел Server без ошибки подключения.
Версии клиента сами по себе ещё не доказывают, что сервер запущен.

## Шаг 2. Создать рабочую папку

Используй новую пустую папку:

```bash
mkdir -p ~/Projects/ojs-learning/docker
cd ~/Projects/ojs-learning
```

В ней мы создадим следующую структуру:

```text
ojs-learning/
  compose.yaml
  .env
  .gitignore
  docker/
    bootstrap.php
    apache-local.conf
    php.ini
```

Во всех следующих командах терминал должен находиться в `~/Projects/ojs-learning`.
Файлы можно создавать любым текстовым редактором. Например, команда
`nano compose.yaml` откроет редактор; для сохранения нажми Ctrl+O, Enter,
для выхода — Ctrl+X. Сохраняй обычный текст, без расширения `.txt`.

Наш прежний стенд использует те же порты. Если он работает, останови его:

```bash
cd /Users/shemchuk/Projects/vestnik
docker compose stop
cd ~/Projects/ojs-learning
```

Это не удаляет прежний журнал. Новый проект будет называться `ojs-learning`
и получит отдельные контейнеры и тома.

## Шаг 3. Создать пароли

Получи два случайных значения:

```bash
openssl rand -hex 24
openssl rand -hex 24
```

Создай файл `.env` и впиши первое значение как пароль пользователя базы,
второе — как пароль администратора базы:

```dotenv
OJS_DB_PASSWORD=ВСТАВЬ_ПЕРВОЕ_ЗНАЧЕНИЕ
DB_ROOT_PASSWORD=ВСТАВЬ_ВТОРОЕ_ЗНАЧЕНИЕ
```

Замени заглушки полностью. Пароли должны быть разными, без пробелов.

```bash
chmod 600 .env
```

Создай `.gitignore`:

```gitignore
.env
```

`.env` читает Docker Compose и подставляет значения в конфигурацию.
Это не пароль для входа в журнал. Пароль администратора OJS зададим позже.

## Шаг 4. Описать контейнеры

Создай `compose.yaml` и вставь:

```yaml
name: ojs-learning

services:
  db:
    image: mariadb:11.8
    environment:
      MARIADB_DATABASE: ojs
      MARIADB_USER: ojs
      MARIADB_PASSWORD: ${OJS_DB_PASSWORD:?Set OJS_DB_PASSWORD in .env}
      MARIADB_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:?Set DB_ROOT_PASSWORD in .env}
    volumes:
      - db_data:/var/lib/mysql
    healthcheck:
      test: [CMD, healthcheck.sh, --connect, --innodb_initialized]
      interval: 5s
      timeout: 5s
      retries: 30
    restart: unless-stopped

  ojs:
    image: pkpofficial/ojs:3_5_0-5
    platform: linux/amd64
    user: "0:0"
    environment:
      SERVERNAME: localhost
      PKP_CONF: /var/www/html/config.inc.php
      PKP_CLI_INSTALL: "0"
      OJS_DB_PASSWORD: ${OJS_DB_PASSWORD}
    ports:
      - "127.0.0.1:8080:80"
    volumes:
      - ojs_app:/var/www/html
      - ojs_files:/var/www/files
      - ./docker/bootstrap.php:/opt/vestnik/bootstrap.php:ro
      - ./docker/php.ini:/usr/local/etc/php/conf.d/vestnik.ini:ro
      - ./docker/apache-local.conf:/etc/apache2/conf-enabled/vestnik-local.conf:ro
    command: [sh, -c, "php /opt/vestnik/bootstrap.php && chown www-data:www-data /var/www/files && exec /usr/local/bin/pkp-start"]
    depends_on:
      db:
        condition: service_healthy
      mailpit:
        condition: service_started
    restart: unless-stopped

  mailpit:
    image: axllent/mailpit:latest
    ports:
      - "127.0.0.1:8025:8025"
    environment:
      MP_DATABASE: /data/mailpit.db
    volumes:
      - mail_data:/data
    restart: unless-stopped

volumes:
  db_data:
  ojs_app:
  ojs_files:
  mail_data:
```

### Как читать этот файл

- `name` — имя проекта. По нему Docker отделяет этот стенд от предыдущего.
- `services` — три приложения, которые должны работать вместе.
- `image` — готовый образ, из которого создаётся контейнер.
- `environment` — параметры, передаваемые контейнеру.
- `${OJS_DB_PASSWORD}` — подстановка из `.env`.
- `ports` — связь порта компьютера с портом контейнера. `127.0.0.1:8080:80`
  означает: локальный порт 8080 направляется на Apache внутри контейнера, порт 80.
- `volumes` — места, которые переживают удаление контейнера, и подключения
  наших конфигурационных файлов. Суффикс `:ro` запрещает контейнеру менять
  подключённый файл.
- `healthcheck` — проверка готовности базы. OJS ждёт успешной проверки базы.
- `restart: unless-stopped` — контейнер может автоматически перезапускаться,
  пока ты явно его не остановил.

MariaDB выбран как совместимая с MySQL база для этого стенда.
Данные базы находятся в `db_data`. OJS не подключается к ней через `localhost`:
внутри его контейнера `localhost` означает сам контейнер OJS, поэтому нужен host `db`.

`platform: linux/amd64` нужен для выбранного образа OJS на Apple Silicon.
Он работает через эмуляцию и может быть медленнее. Проверенный тег —
`pkpofficial/ojs:3_5_0-5`; `stable` в нашем прогоне не существовал.
У Mailpit стоит `latest`, поэтому его версия при новом скачивании может отличаться.

`user: "0:0"` нужен стартовой команде для настройки прав файлов;
веб-сервер затем запускается штатной командой образа.

## Шаг 5. Настроить PHP и Apache

Создай `docker/php.ini`:

```ini
upload_max_filesize = 64M
post_max_size = 80M
memory_limit = 256M
max_execution_time = 120
date.timezone = Asia/Novosibirsk
```

Эти параметры разрешают загрузку файлов до 64 МБ, увеличивают лимит памяти
и задают часовой пояс PHP. `post_max_size` должен быть больше лимита одного файла.

Создай `docker/apache-local.conf`:

```apache
# File-based mutexes work under AMD64 emulation in ARM64 Colima.
Mutex fcntl:/var/lock/apache2 default
ServerName localhost
```

На нашем Apple Silicon стенде без настройки `Mutex` Apache падал с ошибкой
`Couldn't create the mpm-accept mutex`. Здесь для блокировок используется `fcntl`.
`ServerName localhost` задаёт локальное имя сервера.

## Шаг 6. Подготовить конфигурацию OJS

Образ уже содержит `config.inc.php`. Нам нужно указать адрес сайта,
каталог рукописей, базу и SMTP, а также создать уникальные секреты.
Для воспроизводимого первого запуска создаём небольшой PHP-файл,
который изменяет эти параметры. Его ты также создаёшь вручную.

Создай `docker/bootstrap.php`:

```php
<?php
// Initialize the test configuration once. Preserve changes from the installer.
$path = '/var/www/html/config.inc.php';
$marker = '/var/www/html/.vestnik-configured';
if (file_exists($marker)) {
    exit(0);
}
$config = file_get_contents($path);
if ($config === false) {
    throw new RuntimeException('OJS configuration is missing');
}
$settings = [
    'general' => [
        'app_key' => '"base64:' . base64_encode(random_bytes(32)) . '"',
        'base_url' => '"http://localhost:8080"',
        'time_zone' => '"Asia/Novosibirsk"',
        'allowed_hosts' => "'[\"localhost\", \"127.0.0.1\"]'",
        'enable_beacon' => 'Off',
    ],
    'database' => [
        'driver' => 'mysqli',
        'host' => 'db',
        'username' => 'ojs',
        'password' => '"' . getenv('OJS_DB_PASSWORD') . '"',
        'name' => 'ojs',
    ],
    'files' => ['files_dir' => '/var/www/files'],
    'security' => [
        'salt' => '"' . bin2hex(random_bytes(32)) . '"',
        'api_key_secret' => '"' . bin2hex(random_bytes(32)) . '"',
    ],
    'email' => [
        'default' => 'smtp',
        'smtp' => 'On',
        'smtp_server' => 'mailpit',
        'smtp_port' => '1025',
    ],
];
foreach ($settings as $section => $values) {
    $pattern = '/(^\[' . preg_quote($section, '/') . '\]\s*\n)(.*?)(?=^\[|\z)/ms';
    $config = preg_replace_callback($pattern, function ($matches) use ($values) {
        $body = $matches[2];
        foreach ($values as $key => $value) {
            $line = '/^\h*;?\h*' . preg_quote($key, '/') . '\h*=.*$/m';
            if (preg_match($line, $body)) {
                $body = preg_replace_callback($line, fn() => "$key = $value", $body, 1);
            } else {
                $body .= "\n$key = $value\n";
            }
        }
        return $matches[1] . $body;
    }, $config, 1);
}
if (file_put_contents($path, $config) === false) {
    throw new RuntimeException('Could not save OJS configuration');
}
chown($path, 'www-data');
touch($marker);
echo "Local OJS configuration initialized.\n";
```

### Что этот файл делает

1. Читает существующий `config.inc.php` из образа.
2. Меняет значения в соответствующих разделах конфигурации.
3. Создаёт случайные ключ и секреты для нового стенда.
4. Записывает конфигурацию и ставит маркер `.vestnik-configured`.

Маркер означает, что настройки уже выполнены. При повторном запуске файл
завершится сразу и не затрёт изменения браузерного установщика.
Название маркера историческое и на имя журнала не влияет.

В разделе `database` используются те же данные, что переданы MariaDB.
`files_dir` находится за пределами публичного каталога Apache:
рукописи должен выдавать OJS с проверкой прав.
В разделе `email` указан Mailpit без SMTP-пароля и TLS, внутри локальной Docker-сети.

Это только подготовка конфигурации. Таблицы OJS и администратора создаст
следующий, браузерный этап установки.

## Шаг 7. Проверить файлы и запустить

Сначала проверь, что Compose понимает файл и видит переменные:

```bash
docker compose config --quiet
```

**Проверка:** команда завершается без ошибок. Обычный `docker compose config`
может вывести подставленные пароли, поэтому для проверки используем `--quiet`.

Теперь скачай образы и создай контейнеры:

```bash
docker compose pull
docker compose up -d
docker compose ps
```

`pull` скачивает образы. `up -d` создаёт сеть, тома и контейнеры, затем
запускает их в фоне. При первом запуске Docker копирует содержимое каталога
приложения из образа в новый том `ojs_app`.

**Проверка:** `db` имеет статус healthy, `ojs` и `mailpit` работают.

Если что-то не запустилось:

```bash
docker compose logs --tail=100 ojs
docker compose logs --tail=100 db
docker compose logs --tail=100 mailpit
```

Открой в браузере:

- `http://localhost:8080` — установщик OJS.
- `http://localhost:8025` — интерфейс Mailpit, пока без писем.

## Шаг 8. Установить OJS через браузер

На странице установки заполни:

| Поле | Что вписать | Почему |
| --- | --- | --- |
| Administrator username | `admin` | Первая учётная запись OJS |
| Administrator password | Свой новый пароль | Для входа в интерфейс OJS |
| Administrator email | `admin@example.test` | Тестовый адрес |
| Primary locale | Russian | Основной язык |
| Additional locales | English | Дополнительный язык |
| Time zone, если есть | `Asia/Novosibirsk` | Как в конфигурации |
| Files directory | `/var/www/files` | Приватный каталог внутри контейнера |
| Database driver | MySQLi / mysqli | Драйвер подключения PHP к MariaDB |
| Database host | `db` | Имя контейнера базы в Docker-сети |
| Database username | `ojs` | Пользователь, созданный MariaDB |
| Database password | Значение `OJS_DB_PASSWORD` из `.env` | Пароль этого пользователя |
| Database name | `ojs` | База, созданная MariaDB |
| Create new database | Выключить | База уже существует, таблиц OJS ещё нет |
| PKP Beacon | Выключить | Как в нашем локальном прогоне |

Не вводи в установщик `DB_ROOT_PASSWORD`: OJS использует отдельного пользователя `ojs`.

Нажми **Install Open Journal Systems** и дождись результата.
На нашем ARM64-стенде это заняло около двух минут. Не отправляй форму повторно,
пока установка ещё выполняется. После успеха войди под созданным администратором.

**Проверка:** открывается администрирование, можно создавать журналы.
Если вместо установщика сразу виден старый журнал, ты используешь существующие
тома, а не новый проект с пустыми данными.

## Шаг 9. Создать журнал

В **Administration → Hosted Journals** создай журнал:

- RU: `Тестовый журнал Вестник`.
- EN: `Vestnik Test Journal`.
- Path: `vestnik-test`.
- Контакт: `Тестовая редакция`, `editor@example.test`.
- Страна: Russia.

В настройках языков включи русский и английский для интерфейса,
форм, подачи и метаданных; основным оставь русский.

**Проверка:** открывается `http://localhost:8080/vestnik-test`.
Установка OJS и создание журнала — разные действия: один экземпляр OJS
может обслуживать несколько журналов.

Для нашего сценария в **Settings → Workflow → Review** выбери:

- Anonymous Reviewer / Anonymous Author.
- Минимум 2 рецензии.
- Срок ответа 1 неделя; рецензии 2 недели.
- Доступ к файлам после согласия рецензента.

## Шаг 10. Проверить письма и сохранение данных

SMTP уже настроен на `mailpit:1025`. Проверь доставку после первой тестовой
подачи или другого действия OJS, отправляющего письмо: оно должно появиться
на `http://localhost:8025`. Пустой Inbox до этого — нормальное состояние.

Останови и снова запусти контейнеры:

```bash
docker compose stop
docker compose up -d
```

**Проверка:** журнал и учётная запись остались. Повторный установщик не появился.

Сохраняемые данные:

| Том | Содержимое |
| --- | --- |
| `db_data` | База MariaDB |
| `ojs_app` | Код OJS, config.inc.php и публичные файлы |
| `ojs_files` | Приватные рукописи и другие файлы OJS |
| `mail_data` | Письма Mailpit |

`docker compose down` удаляет контейнеры и сеть, но сохраняет эти тома.
Не используй `down -v`, если хочешь сохранить журнал: `-v` удаляет тома.
Не меняй пароли простой правкой `.env` после первой установки: существующая
база и конфигурация автоматически не переключатся на новые значения.

## Если застрял

| Симптом | Проверка |
| --- | --- |
| Cannot connect to Docker daemon | Запущена ли Colima, выбран ли контекст colima |
| Порт занят | Остановлен ли предыдущий стенд; свободны ли 8080 и 8025 |
| База не подключается | Host db, пользователь ojs, база ojs, пароль из .env, healthcheck |
| Apache падает с mutex | Есть ли файл apache-local.conf и его подключение в Compose |
| Установщик не открывается | Логи ojs; контейнер работает; подождать старт под эмуляцией |
| Письма не приходят | Работает ли mailpit; адрес SMTP mailpit, порт 1025; UI на 8025 |

В нашем сценарии найдены две отдельные проблемы OJS: сдвиг дат дедлайнов
в письмах на сутки и `Array` вместо ключевых слов в метаданных рецензента.
Они не означают, что развёртывание не удалось; причины ещё не исследованы.

После этих шагов развёртывание закончено. Создание тестовых пользователей,
подача статьи, рецензии и публикация — следующий этап работы с самим OJS.
В исходном проекте последовательность нашего прогона записана в `test-run.md`.

Эта схема повторяет локальный стенд. Для обновления OJS нужна отдельная процедура:
том `ojs_app` сохраняет и код, поэтому смена тега образа сама по себе код в томе
не обновит.
