# OJS: фактическая работа и пошаговое повторение

Версия: **3.5.0.5**. Среда: macOS ARM64, Colima, Docker Compose. Работа: 7–12 октября 2026. Все статьи, аккаунты и письма тестовые.

**Сейчас контейнеры удалены, данные и бэкап сохранены.** Для продолжения существующего журнала достаточно шага 1 и команды `docker compose up -d` в папке проекта. Установщик повторно проходить не нужно.

Дальше описаны выполненные действия и способ повторить их. Для чистого прогона создайте отдельный проект; ID статей, выпусков и рецензий будут другими. Не запускайте архивные скрипты с прежними ID на существующем журнале.

## 1. Запустили Docker

В терминале:

```bash
colima start
docker context use colima
docker version
docker compose version
docker info
```

**Проверка:** у `docker info` есть раздел Server без ошибки. В начале получили `Cannot connect to the Docker daemon`; запуск Colima устранил её. Использованные версии клиента: Docker 24.0.7, Compose 2.23.3. Colima: 4 CPU, около 3.8 GiB RAM.

## 2. Выбрали образ и подготовили отдельную папку

Проверка образа:

```bash
docker manifest inspect pkpofficial/ojs:stable
```

**Получили:** `no such manifest`. Вместо `stable` использовали `pkpofficial/ojs:3_5_0-5`.

Фактический проект расположен в `/Users/shemchuk/Projects/vestnik` и называется `vestnik-ojs`. Для чистого повторения, не затрагивающего старые данные:

```bash
mkdir -p ~/Projects/ojs-repeat/docker
cd ~/Projects/ojs-repeat
```

В новом `compose.yaml` ниже замените `name: vestnik-ojs` на `name: vestnik-repeat`. Остальные команды выполняйте из новой папки. Старый стенд должен быть остановлен, поскольку используются те же порты.

Для повторения на существующих данных:

```bash
cd /Users/shemchuk/Projects/vestnik
```

## 3. Подготовили пароли базы и конфигурацию контейнеров

**Только для нового проекта:** получите два разных случайных значения:

```bash
openssl rand -hex 24
openssl rand -hex 24
```

Создайте `.env`, заменив заглушки полученными значениями:

```dotenv
OJS_DB_PASSWORD=ПЕРВОЕ_ЗНАЧЕНИЕ
DB_ROOT_PASSWORD=ВТОРОЕ_ЗНАЧЕНИЕ
```

```bash
chmod 600 .env
```

В `.gitignore` добавьте:

```gitignore
.env
.local-admin.json
.local-test-users.json
.local-full-users.json
backups/
__pycache__/
```

В существующем проекте `.env` уже есть. Не генерируйте заново пароли для сохранённой базы.

Создайте `compose.yaml` с фактической конфигурацией (в новой папке используйте имя `vestnik-repeat`):

```yaml
name: vestnik-ojs

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

OJS и база соединяются внутри Docker-сети: host базы — `db`, SMTP — `mailpit:1025`. С компьютера открываем OJS на `localhost:8080`, Mailpit — на `localhost:8025`. Порты доступны только локально.

`platform: linux/amd64` использован для выбранного образа на ARM64. Своего образа не собирали. Тома отдельно сохраняют базу, приложение, рукописи и тестовую почту.

## 4. Настроили PHP, Apache и config.inc.php

Создайте `docker/php.ini`:

```ini
upload_max_filesize = 64M
post_max_size = 80M
memory_limit = 256M
max_execution_time = 120
date.timezone = Asia/Novosibirsk
```

Создайте `docker/apache-local.conf`:

```apache
# File-based mutexes work under AMD64 emulation in ARM64 Colima.
Mutex fcntl:/var/lock/apache2 default
ServerName localhost
```

**Проблема:** Apache не мог создать mutex и не запускался. **Решение:** переключили механизм блокировок на `fcntl`. Причина сбоя именно в разнице архитектур не доказана.

Создайте `docker/bootstrap.php`:

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

Этот файл при первом запуске меняет существующий `config.inc.php`: базу, SMTP, адрес, часовой пояс и каталог рукописей. Секреты создаются случайно. Маркер `.vestnik-configured` предотвращает повторное затирание настроек установщика. Файлы рукописей размещены в `/var/www/files`, вне публичного каталога Apache.

## 5. Запустили контейнеры и установили OJS

```bash
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
```

**Проверка:** база healthy, OJS и Mailpit запущены. Если приложение не открывается:

```bash
docker compose logs --tail=100 ojs
docker compose logs --tail=100 db
```

На чистом стенде откройте `http://localhost:8080`. В установщике задайте:

| Поле | Значение |
|---|---|
| Administrator username | `admin` |
| Administrator password | Собственный пароль для входа в OJS |
| Administrator email | `admin@example.test` |
| Primary locale / Additional locales | Russian / English |
| Files directory | `/var/www/files` |
| Database driver | MySQLi |
| Database host | `db` |
| Database username / name | `ojs` / `ojs` |
| Database password | Значение `OJS_DB_PASSWORD` из `.env` |
| Create new database | Выключить: база уже создана MariaDB |
| PKP Beacon | Выключить |

Нажмите **Install Open Journal Systems**, дождитесь завершения и войдите администратором. `DB_ROOT_PASSWORD` в форму не вводится. Если виден существующий журнал, используются сохранённые тома — это не чистая установка.

**Фактический результат:** администрирование открылось, установку завершили. Полное время развёртывания не измеряли.

![Администрирование после установки OJS.](/Users/shemchuk/Projects/vestnik/screenshots/ojs-admin-installed.jpg)

*Администрирование после установки OJS.*

## 6. Создали журнал, языки и информационные страницы

Под администратором: **Administration → Hosted Journals → Create Journal**.

- Название RU: `Тестовый журнал Вестник`.
- Название EN: `Vestnik Test Journal`.
- Path: `vestnik-test`.
- Контакт: `Тестовая редакция`, `editor@example.test`.
- Страна: Russia.

В настройках журнала включили RU/EN для интерфейса, форм, подачи и метаданных; основным оставили русский. Проверили раздел «Научные статьи».

**Проверка:** открывается `http://localhost:8080/vestnik-test/ru`.

Информационные страницы и руководство автора заполнили сокращённой адаптацией текстов с [сайта журнала](https://intechngu.elpub.ru/jour) и [правил подачи](https://intechngu.elpub.ru/jour/about/submissions). Полный сайт и архивы не переносили. Для повторения в Settings → Journal заполняются описание и разделы журнала, в Settings → Workflow → Submission — Author Guidelines и Submission Checklist.

В руководство внесли: русский/английский язык рукописи, MS Word, Times New Roman 11, одинарный интервал, стандартные поля и выравнивание по ширине. В самом тесте дополнительно принимали LaTeX ZIP.

![Русский и английский включены в настройках журнала.](/Users/shemchuk/Projects/vestnik/screenshots/ojs-test-journal-languages.jpg)

*Русский и английский включены в настройках журнала.*

## 7. Настроили рецензирование и форму

**Settings → Workflow → Review**:

1. Выберите **Anonymous Reviewer / Anonymous Author**.
2. Минимум подтверждённых рецензий — **2**.
3. Доступ к файлам — после согласия рецензента.
4. В исходной настройке: ответ на приглашение 1 неделя, рецензия 2 недели. Для проверки напоминаний позже использовали короткие сроки.

В **Review Forms** создали форму. В **Form Items** добавили вопрос с четырьмя вариантами:

- публиковать как есть;
- после исправлений;
- нужна ещё рецензия;
- не публиковать.

После сохранения заново открыли пункты формы: текст и варианты сохранились. При назначении рецензента выбрали эту форму.

**Обнаружили:** свои четыре варианта не заменяют штатный обязательный список из шести рекомендаций. Рецензент заполняет оба. Это требует согласования списков или доработки формы.

На русском часть кнопок Users & Roles показывалась как `##invitation...##` / `##userAccess...##`. На английском этот экран отображался корректно, поэтому рабочие действия преимущественно выполняли в EN. Нужно проверить загрузку локализации и дополнить отсутствующие строки.

![Сохранённые пункты пользовательской формы рецензирования.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/02-form-items.jpg)

*Сохранённые пункты пользовательской формы рецензирования.*

## 8. Подготовили аккаунты

В полном прогоне были:

| Логин | Роль |
|---|---|
| admin | Администратор сайта |
| chiefeditor | Journal editor — главный редактор в тесте |
| editor | Journal editor — ведущий редактор |
| reviewer1 … reviewer4 | Reviewer |
| reviewer5 | Reviewer + Editorial Board Member |
| author, author2, author3 | Author |

Фактически аккаунты создали штатным **UserImportExportPlugin**: экспортировали существующие определения ролей, подготовили XML, проверили его по схеме OJS и импортировали. Прямых изменений таблиц БД не делали. У двух рецензентов общие интересы; один совмещает роли рецензента и члена редколлегии.

**Для ручного повторения без подготовки XML:** в Settings → Users & Roles → Users используйте **Invite to Role**, отправьте приглашение на тестовый email, откройте письмо в Mailpit и завершите регистрацию. Это альтернативный путь подготовки аккаунтов, не способ, которым создавали аккаунты в нашем прогоне. Весь путь приглашения нового пользователя отдельно не тестировали.

**Точный путь подготовки XML в нашем проекте:** базовый экспорт пользователей/ролей получите через Tools → Import/Export → Users XML Plugin. Сохранённый файл нужен скрипту как `/tmp/vestnik-users-base.xml`. Пароли тестовых аккаунтов находятся в закрытых локальных JSON, в отчёт не включены.

Листинг `docker/import-full-users.php`: сохраните его в новой папке, если повторяете XML-путь. Он читает базовый экспорт и JSON аккаунтов, создаёт XML и проверяет схему:

```php
<?php
$ns='http://pkp.sfu.ca';$d=new DOMDocument();$d->load('/tmp/vestnik-users-base.xml');$users=$d->getElementsByTagNameNS($ns,'users')->item(0);while($users->firstChild)$users->removeChild($users->firstChild);
$add=function($p,$n,$v,$a=[])use($d,$ns){$e=$d->createElementNS($ns,$n);$e->appendChild($d->createTextNode($v));foreach($a as$k=>$val)$e->setAttribute($k,$val);$p->appendChild($e);return$e;};
foreach(json_decode(file_get_contents('/tmp/full-users.json'),true)as$a){$u=$d->createElementNS($ns,'user');$users->appendChild($u);foreach(['ru','en']as$l)$add($u,'givenname',$a['givenName'],['locale'=>$l]);foreach(['ru','en']as$l)$add($u,'familyname',$a['familyName'],['locale'=>$l]);$add($u,'country','RU');$add($u,'email',$a['email']);$add($u,'username',$a['username']);$p=$add($u,'password','',['is_disabled'=>'false','must_change'=>'false','encryption'=>'bcrypt']);$add($p,'value',password_hash($a['password'],PASSWORD_BCRYPT));$add($u,'date_registered','2026-10-12 00:00:00');$add($u,'date_validated','2026-10-12 00:00:00');$add($u,'locales','ru:en');foreach($a['roles']as$r){$m=$add($u,'user_user_group','');$add($m,'user_group_ref',$r);$add($m,'date_start','2026-10-12 00:00:00');$add($m,'masthead','false');}if(in_array('Reviewer',$a['roles']))$add($u,'review_interests','информационные технологии:алгоритмы');}
if(!$d->schemaValidate('/var/www/html/lib/pkp/plugins/importexport/users/pkp-users.xsd'))throw new Exception('invalid');$d->save('/tmp/full-users.xml');echo "XML valid\n";
```

Пример команд подготовки второй группы аккаунтов с существующими файлами проекта:

```bash
docker compose cp /ПУТЬ/К/экспорту.xml ojs:/tmp/vestnik-users-base.xml
docker compose cp .local-full-users.json ojs:/tmp/full-users.json
docker compose cp docker/import-full-users.php ojs:/tmp/import-full-users.php
docker compose exec -T ojs php /tmp/import-full-users.php
docker compose cp ojs:/tmp/full-users.xml ./full-users.xml
```

Полученный `full-users.xml` импортируйте тем же штатным плагином. Для исходных editor/author/reviewer1/reviewer2 аналогичный скрипт — `docker/prepare-test-users.php`; он читает `/tmp/vestnik-test-users.json`. Сам JSON должен содержать выбранные вами логины и пароли, а названия ролей соответствовать экспорту. На существующем журнале повторный импорт тех же аккаунтов не требуется.

**Проверка:** в Users & Roles видны 11 аккаунтов и нужные роли. Для проверки чужих прав входите непосредственно под их логином в отдельном приватном окне. Администраторский Login As удобен для смены роли, но API-утечку проверяли отдельной собственной сессией рецензента.

![Аккаунты и роли полного прогона.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/00-users.jpg)

*Аккаунты и роли полного прогона.*

## 9. Подготовили файлы статей

Для повторения используйте файлы в `test-data/full-run/` исходного проекта:

| Файл | Назначение |
|---|---|
| A-original.docx | А: первоначальный файл, прямое форматирование, рисунок и формула |
| A-formatted.docx | А: исправление оформления после входной проверки |
| A-v2.docx | А: доработка по рецензиям |
| A-v2.pdf | А: готовая гранка, сделанная вне OJS |
| A-response-v2.txt | Подготовленный ответ по пунктам; в OJS отправили текст обсуждением |
| B-latex.zip | Б: tex, bib и рисунок |
| B-author.pdf | Б: отдельный PDF автора |
| C-styled.docx | В: короткая статья со стилями Title / Heading 1 |
| C-styled.pdf | В: готовый PDF |

DOCX подготовили скриптами, затем отрендерили и визуально проверили PDF. В свойствах обезличенных DOCX очистили автора и lastModifiedBy. Формула в тестовой А набрана текстом; математическую конвертацию в JATS не проверяли. PDF Б подготовлен отдельно; успешную компиляцию её LaTeX-архива не утверждаем.

Генератор исходников сохранён в `docker/make-full-test-data.py`, подготовка старых файлов — в `docker/make-test-article.py` и `docker/make-test-revision.py`. Повторный запуск генератора перезаписывает тестовые исходники; для воспроизведения текущего сценария достаточно готовых файлов.

## 10. Сначала выполнили сокращённый прогон 7 октября

Первой была статья **№1** «Сравнение алгоритмов поиска дубликатов». Её подали, назначили editor и двух рецензентов, получили замечания, отправили на доработку и создали Round 2.

Из-за ограничения времени повторные отзывы, отдельную корректуру и вторую статью тогда пропустили. Принятие подтвердили с предупреждением о минимуме рецензий. PDF опубликовали в тестовом выпуске №1. Это сокращённая проверка, а не полный сценарий.

При полном прогоне эту статью и выпуск сохранили. Поэтому в конце есть **четыре** статьи: старая №1 и новые А, Б, В.

![Второй раунд первой статьи в сокращённом прогоне.](/Users/shemchuk/Projects/vestnik/screenshots/ojs-review-round-2.jpg)

*Второй раунд первой статьи в сокращённом прогоне.*

## 11. Подали новую статью А

Войдите как `author`, откройте **New Submission / Start A New Submission**:

1. Язык — Russian; раздел — «Научные статьи».
2. Подтвердите требования подачи.
3. Загрузите `A-original.docx` как Article Text.
4. Заполните название, аннотацию и ключевые слова на RU и EN.
5. Добавьте трёх авторов: author, author2, author3 с тестовыми email.
6. Назначьте основного контакта и завершите отправку.

Названия:

- RU: **А Проверка поиска дубликатов в массивах**.
- EN: **A Testing duplicate detection in arrays**.

**Получили:** А — submissionId=2, publicationId=2. При повторении запишите собственные ID. Автор видит Submission, редактор — новую подачу. Mailpit получил сообщения, в том числе соавторам.

**Проблема:** `primaryContactId` позволяет только один основной контакт. Второго контактного автора, требуемого сценарием, не получили; письма всем соавторам это требование не заменяют.

![Новая А поступила в редакцию.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/03-A-submitted.jpg)

*Новая А поступила в редакцию.*

![Три соавтора и один основной контакт.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/03-A-contributors.jpg)

*Три соавтора и один основной контакт.*

## 12. Вернули А на исправление оформления

Под главным редактором назначьте editor участником статьи. Ведущий редактор на этапе Submission создаёт **Pre-Review Discussion** с замечаниями по оформлению и включает автора в участников.

Под автором откройте обсуждение, ответьте и приложите `A-formatted.docx`. Под редактором проверьте файл и ответ; затем выберите **Send to Review** и передайте исправленный файл в первый раунд.

**Получили:** исправление доступно редакции. Это возврат через обсуждение; отдельного статуса «правка оформления» не создавали.

Дополнительно проверили **Decline Submission** на входной стадии временной статьи №6: она стала Declined. Проба не относится к А/Б/В; после фиксации результата удалена штатным репозиторием приложения.

![Ответ автора и исправление оформления.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/04-A-author-formatting.jpg)

*Ответ автора и исправление оформления.*

## 13. Пригласили и заменили рецензентов А

Под editor: **Review → Round 1 → Add Reviewer**. Для каждого назначения выберите файл, пользовательскую форму, двойное слепое рецензирование и сроки; отправьте приглашение.

Последовательность:

1. Пригласите reviewer1, reviewer2, reviewer3.
2. Под reviewer1 откройте назначение и откажитесь.
3. Под reviewer2 примите приглашение.
4. Под reviewer3 не отвечайте — этим имитируется молчание, реального многодневного ожидания не было.
5. Под editor пригласите reviewer4; под reviewer4 примите.
6. Под editor отмените приглашение reviewer3.

**Получили:** отказ / согласие / ожидание / согласие, затем два действующих рецензента. Отменённое неподтверждённое назначение исчезает из списка; история подтверждается промежуточным снимком и письмом об отмене.

Письма проверьте в `http://localhost:8025` поиском по адресам рецензентов.

![Состояния четырёх приглашений перед отменой молчащего.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/05-A-reviewer-states.jpg)

*Состояния четырёх приглашений перед отменой молчащего.*

![Приглашение рецензенту в Mailpit.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/05-review-invitation-mail.jpg)

*Приглашение рецензенту в Mailpit.*

## 14. Проверили анонимность — нашли раскрытие через API

Под назначенным рецензентом:

1. До согласия попробуйте скачать файл — рукопись не должна выдаваться.
2. После согласия откройте страницу, скачайте DOCX, проверьте текст и File → Properties / сведения о документе.
3. Посмотрите приглашение: имя автора отсутствует.

В нашей проверке интерфейс, текст, свойства DOCX и приглашение не раскрывали авторов. Но файл был обезличен нами заранее — автоматическую очистку OJS это не доказывает.

**Проверка утечки:** войдите непосредственно как назначенный рецензент. Пока статья НЕ опубликована, откройте в том же браузере:

```text
http://localhost:8080/vestnik-test/api/v1/submissions/SUBMISSION_ID/publications/PUBLICATION_ID/contributors
```

Для нашей А было `/submissions/2/publications/2/contributors`. `submissionId` виден в адресе workflow; `currentPublicationId` можно получить из разрешённого рецензенту ответа `/api/v1/submissions/SUBMISSION_ID`.

**Фактический ответ:** HTTP 200, три автора с `fullName` и `email`:

```json
[
  {
    "fullName": "Тестовый Автор",
    "email": "author@example.test"
  },
  {
    "fullName": "Второй Автор",
    "email": "author2@example.test"
  },
  {
    "fullName": "Третий Автор",
    "email": "author3@example.test"
  }
]
```

Ответ сохранён **до публикации** в `evidence/full-run/A-reviewer-contributors-current.json`. А теперь опубликована: её текущий ответ не служит доказательством нарушения. Для самостоятельного повторения нужна новая неопубликованная статья на Review.

**Вывод:** двойное слепое рецензирование нарушено через API. Исправление не выполняли. Нужно исследовать авторизацию и выдачу contributors, закрыть рецензенту авторов до публикации и проверить соседние API и роли. Возможность исправить исключительно плагином пока не подтверждена.

## 15. Получили первые отзывы и проверили напоминания

Под reviewer2 и reviewer4:

1. Примите приглашение.
2. Пройдите инструкции рецензирования.
3. Откройте Download & Review, прочитайте файл.
4. Заполните пользовательскую форму, публичные замечания и рекомендацию.
5. Отправьте отзыв.

Reviewer2 — «после исправлений», reviewer4 — «публиковать». Затем editor открыл оба отзыва и нажал **Confirm** для каждого: одного факта отправки недостаточно для минимума подтверждённых рецензий.

![Форма с четырьмя пользовательскими вариантами и штатной рекомендацией.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/07-A-review-form.jpg)

*Форма с четырьмя пользовательскими вариантами и штатной рекомендацией.*

![Отправленный отзыв.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/07-A-review-completed.jpg)

*Отправленный отзыв.*

Напоминания проверили на ожидающих назначениях второго раунда **до отправки повторных отзывов**. Сроки назначения были 13/14 октября; в настройках использовали напоминание за два дня до сроков. Запустили штатную задачу и очередь:

```bash
docker compose exec -T ojs php lib/pkp/tools/scheduler.php test \
  --name='PKP\task\ReviewReminder'
docker compose exec -T ojs php lib/pkp/tools/jobs.php run
```

**Получили:** два задания и два письма в Mailpit. Проверена генерация уведомлений вручную вызванной задачей. Постоянный cron не настроили. Для автономной работы нужен регулярный запуск scheduler/worker; повторный ручной запуск может повторно отправить тестовые письма.

**Проблема:** в приглашениях дата на сутки раньше формы — форма 13/14 октября, письмо 12/13 октября. Причина не исследована; проверить часовые пояса и преобразование дат.

![Реальное письмо-напоминание, сформированное штатной задачей.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/07-reminder-mail.jpg)

*Реальное письмо-напоминание, сформированное штатной задачей.*

## 16. Отправили А на доработку и получили v2

Под editor после подтверждения обоих отзывов выберите **Resubmit for Review**. В письме вставьте публичные замечания; отправьте решение автору.

Под author:

1. Откройте статью с требованием доработки.
2. Через **Upload Revisions** загрузите `A-v2.docx`.
3. В обсуждении отправьте ответ по пунктам: граничные случаи, псевдокод, оценка памяти и проверка рисунка/формулы.

**Получили:** новая версия доступна редакции; ответ автора сохранён обсуждением. `A-response-v2.txt` подготовлен локально, но отдельным файлом в OJS не загружен. В письме автору рецензенты обозначены номерами, их имён нет.

## 17. Выполнили Round 2 и приняли А

Под editor создайте **New Review Round**, передайте только версию v2, назначьте reviewer2 и reviewer4 повторно. Под ними примите назначения и отправьте положительные отзывы. Под editor прочитайте, подтвердите оба и выберите **Accept Submission**, затем переведите в Production через штатный редакционный переход.

**Получили:** два полных раунда, два повторных отзыва, принятие после подтверждения обоих. Минимум рецензий в полном прогоне не обходили.

**Техническая сложность:** испробованный REST-вызов копирования v2 вернул 401. В новый раунд загрузили те же байты штатным способом. Для ручного повторения выберите v2 среди доступных файлов либо используйте Upload/Add File в нужном раунде. Ядро не меняли.

## 18. Загрузили PDF и получили согласие автора

Под editor: **Production → Publication → Galleys → Add Galley**. Создайте гранку с label `PDF`, locale Russian и загрузите `A-v2.pdf`.

В **Production Discussions** создайте запрос корректуры автору. Под author откройте PDF, проверьте его и ответьте подтверждением в обсуждении.

**Получили:** гранка А galleyId=2, fileId=15. Автор скачал 39 646 байт, точно совпадающих с подготовленным PDF. Это ручное согласование сообщением, не отдельная кнопка подтверждения. PDF сделан вне OJS; конвертацию внутри приложения не выполняли.

![Запрос корректуры и подтверждение в авторском кабинете.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/09-A-author-proof.jpg)

*Запрос корректуры и подтверждение в авторском кабинете.*

## 19. Опубликовали А в выпуске текущего квартала

Под editor: **Issues → Future Issues → Create Issue**:

- Volume 1, Number 4, Year 2026.
- RU: `IV квартал 2026`.
- EN: `Fourth quarter 2026`.

В статье: **Publication → Issue** назначьте созданный выпуск, страницы `1–3`, дату публикации. Завершите планирование публикации; в неопубликованном выпуске статья сначала имеет статус Scheduled.

Затем в Issues откройте выпуск и выберите **Publish Issue**.

**Получили:** issueId=2, А стала Published. Проверили публичную страницу и скачивание PDF без входа.

## 20. Подали Б в LaTeX и отклонили после двух отзывов

Под author2 создайте новую подачу:

- RU: `Б Анализ времени ожидания в очереди`.
- EN: `B Analysing waiting time in a queue`.
- Двуязычная аннотация и ключевые слова.
- Файлы: `B-latex.zip` и `B-author.pdf`.

Под редактором назначьте editor, отправьте на Review и передайте PDF для оценки. Пригласите reviewer1 и reviewer5. Под каждым примите приглашение, заполните отзыв и отрицательную рекомендацию. Под editor подтвердите оба и выберите **Decline Submission**, отправьте автору замечания.

**Получили:** Б submissionId=3, статус Declined, письмо пришло author2 в Mailpit. Имена рецензентов в публичных замечаниях не раскрыты. ZIP принят; OJS его не компилировала.

В нашем автоматизированном вызове длинное тело письма попало также в тему — это ошибка подготовки тестового письма, не подтверждённый дефект OJS. При ручном повторении задайте короткую тему отдельно от текста.

![ZIP LaTeX и отдельный PDF приняты системой.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/11-B-files.jpg)

*ZIP LaTeX и отдельный PDF приняты системой.*

![Два отрицательных отзыва и отказ по Б.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/11-B-declined-reviews.jpg)

*Два отрицательных отзыва и отказ по Б.*

![Письмо об отказе в Mailpit.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/11-B-rejection-mail.jpg)

*Письмо об отказе в Mailpit.*

## 21. Подали В и добавили её в уже опубликованный выпуск

Под author3 создайте подачу с `C-styled.docx`:

- RU: `В Короткая заметка о двоичном поиске`.
- EN: `C A short note on binary search`.
- Аннотация и ключевые слова RU/EN.

Под editor назначьте редактора, используйте **Accept and Skip Review**, затем перевод в Production. Создайте PDF-гранку, загрузите `C-styled.pdf`, назначьте **тот же опубликованный выпуск** и страницу `4`, нажмите Publish.

**Получили:** В submissionId=4, Published; в выпуске появились А и В. PDF А побайтно не изменился. В первоначально получила ошибочный заголовок о сортировке; метаданные исправили на двоичный поиск, соответствующий DOCX. Отдельную корректуру В не выполняли — использовали короткий путь сценария.

![Финальный выпуск с А и В.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/12-issue-A-C.jpg)

*Финальный выпуск с А и В.*

## 22. Проверили публичный сайт и кабинеты

Без входа, в приватном окне:

```text
http://localhost:8080/vestnik-test/ru/article/view/2
http://localhost:8080/vestnik-test/en/article/view/2
http://localhost:8080/vestnik-test/ru/issue/view/2
http://localhost:8080/vestnik-test/ru/issue/archive
http://localhost:8080/vestnik-test/ru/search
```

При повторении подставьте собственные ID. Проверили RU/EN, PDF, выпуск, два выпуска в архиве и поиск по «дубликатов». Поиск возвращает новую А и прежнюю №1. В RU виден непереведённый ключ строки количества результатов.

Под chiefeditor откройте **Editor Dashboard → Published**. Получили три опубликованные (№1, А, В) и одну Declined (Б). В **Filters → Issues** выбрали выпуск IV квартала: осталось ровно две статьи. Активных в финале нет.

![Публичная страница А на русском.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/13-A-public-ru.jpg)

*Публичная страница А на русском.*

![Английская страница А.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/13-A-public-en.jpg)

*Английская страница А.*

![Поиск и непереведённая строка количества результатов.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/13-search-ru.jpg)

*Поиск и непереведённая строка количества результатов.*

![Архив сохранённых тестовых выпусков.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/13-archive.jpg)

*Архив сохранённых тестовых выпусков.*

![Применённый фильтр выпуска в кабинете главного редактора.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/14-chief-issue-filter.jpg)

*Применённый фильтр выпуска в кабинете главного редактора.*

## 23. Проверили экспорт OAI-PMH; JATS не проверяли

В терминале:

```bash
mkdir -p evidence/full-run
curl --fail 'http://localhost:8080/vestnik-test/oai?verb=Identify' \
  -o evidence/full-run/oai-identify.xml
curl --fail 'http://localhost:8080/vestnik-test/oai?verb=ListRecords&metadataPrefix=oai_dc' \
  -o evidence/full-run/oai-records.xml
```

**Фактически:** сервер возвращал XML Identify и ListRecords, ответы сохранены. Это OAI-PMH с метаданными, **не JATS полного текста**.

**Вкладку JATS / настройки JATS и работу с JATS-файлом не пробовали.** DOCX/LaTeX → JATS не запускали; JATS-гранку не загружали; рендер XML и валидность JATS не проверяли. Поэтому отметки «конвертация JATS работает» в результатах нет.

Следующий отдельный тест — найти соответствующий экран/модуль в установленной версии, зафиксировать его назначение, загрузить валидный тестовый JATS, если экран это поддерживает, проверить ошибки и публичный просмотр. Наличие вкладки само по себе не доказывает конвертацию DOCX/LaTeX. Этот тест ещё не выполнен, контейнеры ради него сейчас не запускали.

## 24. Написали API-логгер смены состояния

Использовали редакторскую сессию, читали статьи через `/vestnik-test/api/v1/submissions?count=100`, сравнивали `status` и `stageId` с прошлым снимком.

В существующем проекте:

```bash
python3 docker/ojs-status-monitor.py
# Теперь выполните изменение этапа или публикацию в интерфейсе.
python3 docker/ojs-status-monitor.py
```

Скрипт использует локальные файлы аккаунтов `.local-test-users.json` и `.local-full-users.json`. На новом стенде они должны соответствовать созданным вами аккаунтам; чужие пароли не копируются в отчёт. Первое наблюдение создаёт исходное состояние, второй запуск фиксирует изменения.

Листинг фактически использованного логгера:

```python
"""Poll the authenticated OJS REST API and log status/stage changes.
Run manually or from an external scheduler. Uses the existing local editor account.
This demo does not install a plugin or modify OJS core.
"""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import json,datetime
client=SourceFileLoader('ojs_client',str(Path(__file__).with_name('ojs-api-client.py'))).load_module()
root=Path(__file__).resolve().parents[1]; dest=root/'evidence/full-run'; dest.mkdir(parents=True,exist_ok=True)
statepath=dest/'status-monitor-state.json';old=json.loads(statepath.read_text()) if statepath.exists() else {}
s=client.session('editor');r=s.get('http://localhost:8080/vestnik-test/api/v1/submissions?count=100');assert r.status_code==200,r.text
new={str(x['id']):{'status':x['status'],'stageId':x['stageId']} for x in r.json()['items']}
changes=[{'time':datetime.datetime.now().astimezone().isoformat(),'submissionId':int(k),'before':old.get(k),'after':v} for k,v in new.items() if k in old and old[k]!=v]
with (dest/'status-changes.jsonl').open('a') as out:
 for item in changes:out.write(json.dumps(item,ensure_ascii=False)+'\n')
statepath.write_text(json.dumps(new,indent=2));print(json.dumps({'observed':len(new),'changes':changes},ensure_ascii=False))
```

Для восстановления скрипта в новой папке сохраните рядом `docker/ojs-api-client.py` с таким содержимым (без отдельного запуска клиента):

```python
import json,re,urllib.request,urllib.parse,http.cookiejar
from pathlib import Path
root=Path(__file__).resolve().parents[1];base='http://localhost:8080/vestnik-test/en'
class LocalPolicy(http.cookiejar.DefaultCookiePolicy):
 def return_ok_domain(self,cookie,request):
  if cookie.domain in ('.localhost','localhost'): return True
  return super().return_ok_domain(cookie,request)
class Response:
 def __init__(self,r): self.status_code=r.code; self.content=r.read();self.text=self.content.decode('utf8','replace')
 def json(self):return json.loads(self.text)
class Client:
 def __init__(self):self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar(policy=LocalPolicy())));self.headers={}
 def request(self,method,url,data=None,json=None,headers=None):
  h=dict(self.headers);h.update(headers or {}); body=None
  if json is not None:body=__import__('json').dumps(json).encode();h['Content-Type']='application/json'
  elif isinstance(data,dict):body=urllib.parse.urlencode(data,doseq=True).encode()
  elif data is not None:body=data
  try:r=self.opener.open(urllib.request.Request(url,body,h,method=method),timeout=60)
  except urllib.error.HTTPError as e:r=e
  return Response(r)
 def get(self,u):return self.request('GET',u)
 def post(self,u,**kw):return self.request('POST',u,**kw)
 def put(self,u,**kw):return self.request('PUT',u,**kw)
def session(username):
 rows=json.loads((root/'.local-test-users.json').read_text())+json.loads((root/'.local-full-users.json').read_text());a=next((a for a in rows if a['username']==username),None)
 if username=='admin':a=json.loads((root/'.local-admin.json').read_text())
 s=Client();html=s.get(base+'/login').text;token=re.search(r'name="csrfToken"[^>]*value="([^"]+)',html)
 r=s.post(base+'/login/signIn',data={'username':username,'password':a['password'],'csrfToken':token.group(1) if token else ''})
 m=re.search(r'"csrfToken"\s*:\s*"([^"]+)"',r.text) or re.search(r'name="csrfToken"[^>]*value="([^"]+)',r.text)
 if m:s.headers['X-Csrf-Token']=m.group(1)
 s.headers['Accept']='application/json';return s
```

Локальный файл `.local-full-users.json` — массив объектов с полями `username` и `password` для авторизации. Импорт пользователей также использует `givenName`, `familyName`, `email`, `roles`. `.local-test-users.json` содержит первую группу аккаунтов; если все аккаунты перенесены в первый файл, второй может содержать пустой массив `[]`. Это приватные файлы, вне Git. Пример записи с заглушкой:

```json
[{"username":"editor","password":"ПАРОЛЬ_ВАШЕГО_РЕДАКТОРА"}]
```

Он импортирует клиент из `docker/ojs-api-client.py`. Клиент авторизуется обычным логином/паролем, сохраняет cookie и CSRF; отдельный постоянный API-ключ не создавали. Реальный файл клиента сохранён в проекте. Переносить примеры GET на `/en/api/v1` не нужно: REST API вызывается **без языкового сегмента**.

**Получили:** два события А — Review → Production и активная → Published. Лог `evidence/full-run/status-changes.jsonl`:

```json
{"time": "2026-10-12T01:50:39.726546+07:00", "submissionId": 2, "before": {"status": 1, "stageId": 3}, "after": {"status": 1, "stageId": 5}}
{"time": "2026-10-12T01:59:49.653099+07:00", "submissionId": 2, "before": {"status": 1, "stageId": 5}, "after": {"status": 3, "stageId": 5}}
```

Это ручной опрос API, не webhook и не установленный плагин. Постоянный сервис не настраивали. Также проверили API пользователей, статей, файлов и публикаций. Назначения рецензентов доступны в данных статьи; часть изменений выполняли через внутренние обработчики форм. Архив автоматизации — `docker/scenario-run/`; он не является безопасным сценарием повторного запуска на нынешних ID.

## 25. Проверили доступ к чужим и приватным данным

1. Под author попробовали получить Б через API `/submissions/3` — HTTP 401.
2. Под author открыли прямую ссылку приватного файла Б — отказ, файл не выдан.
3. Под reviewer3, не назначенным на Б, запросили `/submissions/3` — 401.
4. Без входа открыли прямую ссылку исходника А и внутреннюю ссылку гранки — отказ.
5. Без входа скачали опубликованный PDF А — файл выдан, совпадает с подготовленным.

Для повторения скопируйте URL приватного файла из кабинета имеющего доступ пользователя и откройте под другой ролью/в приватном окне. Не подменяйте приватную ссылку публичным адресом PDF: опубликованный PDF должен быть открыт всем.

**Особенность:** отказ на приватный файл иногда возвращает HTTP 200 с JSON `status=false`. Проверяйте тело, Content-Type и фактические байты, а не только статус HTTP.

Создали временную статью №5 и загрузили через API инертные `.php` и `.html`. API принял файлы: PHP сохранён с расширением `.txt`, HTML — `.html`, вне webroot. Никакого исполняемого payload не было, выполнение кода не проверяли. Это повод проверить допустимые типы и выдачу файлов, но не доказательство RCE.

Фрагмент повторения загрузки через API с уже сохранёнными клиентом и помощниками проекта (создаёт отдельную новую тестовую подачу, а не меняет А/Б/В):

```bash
python3 - <<'PYCODE'
from importlib.machinery import SourceFileLoader
h = SourceFileLoader('workflow', 'docker/ojs-workflow-helpers.py').load_module()
s = h.session('author2')
draft = h.req(s, 'POST', '/submissions', {'locale': 'ru', 'sectionId': 1})
sid = draft['id']
print('ID новой временной подачи:', sid)
for name in ['blocked-upload.php', 'blocked-upload.html']:
    result = h.upload(s, sid, name)
    print(result['id'], result['mimetype'], result['path'])
PYCODE
```

Файлы `blocked-upload.php` и `blocked-upload.html` находятся в `test-data/full-run/` и содержат только инертный тестовый текст. Приведённый фрагмент зависит от помощника проекта; его точный код сохранён в `docker/ojs-workflow-helpers.py`. Не запускайте архивный `security-check.py` повторно: в нём есть прежние ID и неуспешные промежуточные попытки, исправленные позднее. Для очистки новой пробы сначала запишите её ID и используйте штатное удаление с проверкой именно этого ID; старые скрипты очистки автоматически не подходят.

Удаление этих файлов через испробованный REST API вернуло отказ; после бэкапа временную статью удалили штатным репозиторием OJS. Скрипты `docker/cleanup-security-probe.php` и `docker/cleanup-initial-decline-test.php` имеют проверки конкретных ID и состояния. **Для нового прогона их старые ID не использовать.**

Проверили версии стека: PHP 8.3.31, Laravel 12.62.0, MariaDB 11.8.9. Ветки поддерживаются по официальным таблицам; полный аудит CVE зависимостей не выполняли. HTTPS, защита от перебора, MFA, самостоятельная регистрация и восстановление пароля не пройдены отдельным полным тестом.

## 26. Сделали резервную копию

Резервная копия — **дамп базы и архив файлов**, не один SQL. База хранит пользователей, метаданные, отзывы и связи; рукописи и PDF лежат отдельно.

Из папки проекта:

```bash
mkdir -p backups/full-run-2026-10-12
chmod 700 backups/full-run-2026-10-12

docker compose exec -T db sh -c \
  'exec mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction --routines --triggers ojs' \
  > backups/full-run-2026-10-12/ojs.sql

docker compose exec -T ojs \
  tar --hard-dereference -czf - -C /var/www html files \
  > backups/full-run-2026-10-12/ojs.tar.gz

chmod 600 backups/full-run-2026-10-12/ojs.sql \
  backups/full-run-2026-10-12/ojs.tar.gz
shasum -a 256 backups/full-run-2026-10-12/ojs.sql \
  backups/full-run-2026-10-12/ojs.tar.gz \
  > backups/full-run-2026-10-12/SHA256SUMS
```

Фактический скрипт: `sh docker/backup-ojs.sh`. Он выполняет эти действия и **перезаписывает копию в указанной папке**. При новом самостоятельном бэкапе выберите другую папку и измените соответствующий путь восстановления. Делали копию после завершения изменений тестовых статей.

## 27. Пересоздали основной контейнер и восстановили отдельную копию

Сначала проверили сохранение томов:

```bash
docker compose rm -s -f ojs
docker compose up -d ojs
```

**Получили:** другой контейнер OJS, прежние данные. Это сохранение томов, а не восстановление из бэкапа.

Затем создали `docker/compose.restore.yaml` для настоящего восстановления в отдельные новые тома:

```yaml
name: vestnik-restore
services:
  db:
    image: mariadb:11.8
    environment:
      MARIADB_DATABASE: ojs
      MARIADB_USER: ojs
      MARIADB_PASSWORD: ${OJS_DB_PASSWORD}
      MARIADB_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
    volumes:
      - db_data:/var/lib/mysql
      - ../backups/full-run-2026-10-12/ojs.sql:/docker-entrypoint-initdb.d/ojs.sql:ro
    healthcheck:
      test: [CMD, healthcheck.sh, --connect, --innodb_initialized]
      interval: 5s
      timeout: 5s
      retries: 30
  ojs:
    image: pkpofficial/ojs:3_5_0-5
    platform: linux/amd64
    user: '0:0'
    environment:
      SERVERNAME: localhost
      PKP_CONF: /var/www/html/config.inc.php
      PKP_CLI_INSTALL: '0'
    ports:
      - '127.0.0.1:8081:80'
    volumes:
      - ojs_app:/var/www/html
      - ojs_files:/var/www/files
      - ../backups/full-run-2026-10-12:/restore:ro
      - ./php.ini:/usr/local/etc/php/conf.d/vestnik.ini:ro
      - ./apache-local.conf:/etc/apache2/conf-enabled/vestnik-local.conf:ro
    command: [sh, -c, 'tar xzf /restore/ojs.tar.gz -C /var/www && sed -i s/localhost:8080/localhost:8081/g /var/www/html/config.inc.php && exec /usr/local/bin/pkp-start']
    depends_on:
      db:
        condition: service_healthy
      mailpit:
        condition: service_started
  mailpit:
    image: axllent/mailpit:latest
volumes:
  db_data:
  ojs_app:
  ojs_files:
```

При чистом повторении возьмите именно сделанный вами бэкап и те же пароли базы, которым соответствует сохранённый `config.inc.php`. Restore Compose читает `.env` основного проекта.

Если временная копия ещё не существует:

```bash
docker compose --env-file .env -f docker/compose.restore.yaml up -d
docker compose --env-file .env -f docker/compose.restore.yaml ps
docker compose --env-file .env -f docker/compose.restore.yaml logs --tail=30 ojs
```

**Дождитесь распаковки архива и запуска Apache**, затем откройте `http://localhost:8081/vestnik-test/ru`. Восстановление SQL происходит только при инициализации пустого тома БД. Если требуется повторная проверка, сначала удаляется **только временный проект** командой из шага 29, затем запускается заново.

**Проблема при первом повторном восстановлении:** tar встретил жёсткую ссылку между томами (`Invalid cross-device link`). **Решение:** заново создали архив с `--hard-dereference`, восстановили с пустыми томами.

Проверили в копии четыре статьи, 11 пользователей, названия А/В, страницы выпуска и PDF. SHA-256 PDF А одинаковый в оригинале и копии:

```text
be4ff5d96179968bee54dc67afc9b1cfcdcf6bfb2b599de9adb9bb92e959a2d2
```

Для повторения сравните контрольные суммы скачанных PDF:

```bash
curl --fail 'http://localhost:8080/vestnik-test/ru/article/download/2/2/15' -o /tmp/A-main.pdf
curl --fail 'http://localhost:8081/vestnik-test/ru/article/download/2/2/15' -o /tmp/A-restored.pdf
shasum -a 256 /tmp/A-main.pdf /tmp/A-restored.pdf
```

Подставьте свои ID. Обязательно убедитесь, что оба ответа — PDF, а не HTML/JSON ошибки. Restore Compose используется только для одноразовой проверки: при каждом запуске распаковывает архив.

![Выпуск в отдельной восстановленной копии на 8081.](/Users/shemchuk/Projects/vestnik/screenshots/full-run/16-restored-issue.jpg)

*Выпуск в отдельной восстановленной копии на 8081.*

## 28. Проверили версию, но не выполняли обновление

```bash
docker compose exec -T ojs php tools/upgrade.php check
```

**Получили:**

```text
Code version:      3.5.0.5
Database version:  3.5.0.5
Latest version:    3.5.0.5
Your system is up-to-date
```

Это только проверка версии. **Переход на другую версию и миграция данных не выполнялись.** Смена Docker-тега сама по себе не доказывает обновления: `ojs_app` сохраняет также код приложения.

## 29. Завершили работу и удалили контейнеры

После проверки удалили временный проект **вместе с его тестовыми томами**:

```bash
docker compose --env-file .env -f docker/compose.restore.yaml down -v
```

Основной проект завершили **без удаления томов**:

```bash
docker compose down
docker ps
```

Запущенных контейнеров не осталось. Данные основного журнала и бэкап сохранены. Возобновить существующий журнал:

```bash
colima start
cd /Users/shemchuk/Projects/vestnik
docker compose up -d
```

## Что получилось и что осталось

А прошла входную правку, два раунда, v2, корректуру и публикацию. Б отклонена после двух рецензий. В добавлена в открытый выпуск, А не изменена. Письма, кабинеты, фильтры, OAI-PMH, API-логгер и восстановление проверены. Ядро не меняли.

Основные незакрытые вопросы: раскрытие авторов через API; неполный перевод; один основной контакт вместо двух; два списка рекомендаций; сдвиг дат в письмах; постоянное расписание задач; ограничения загрузки файлов. **JATS-вкладка и конвертация не проверены, миграция между версиями не выполнена.**

Полные ответы API, свойства DOCX и письма — `evidence/full-run/`; оригинальные скриншоты — `screenshots/`; скрипты — `docker/`. Приватные пароли и бэкапы исключены из Git и в этот файл не включены. Подробный прежний протокол с чек-листом сохранён отдельно: `OJS-FULL-RUN.html`.
