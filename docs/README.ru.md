# tg-miniapp-starter (русский)

Шаблон Telegram-бота и Telegram Mini App, который работает на **обычном дешёвом хостинге**:
без Docker, root, systemd и открытых портов. Если на хостинге есть SSH, домен с SSL, cron
и Python 3.11 — этого достаточно.

## Что внутри

- **Один процесс** запускает и бота (aiogram 3, long polling), и веб-часть (FastAPI).
- **Вход без пароля**: `initData` от Telegram проверяется токеном бота.
- **Фото с камеры**: приложение сразу открывает камеру, сжимает фото перед загрузкой,
  сервер ставит в углу дату и время.
- **Закрытые ссылки на фото**: файлы вне веб-папки, каждая ссылка подписана HMAC.
- **Выгрузка в Excel** с живой формулой `SUM` и миниатюрами фото; админ получает её командой `/export`.
- **Скрипты для хостинга**: установка, запуск/остановка, сторож, который не запускает вторую копию,
  ежедневный бэкап, reverse proxy через `.htaccess`.

## Локальный запуск

```bash
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env            # для локальной проверки DEV_MODE=1
uvicorn app.main:app --port 8000
```

Откройте <http://localhost:8000/?dev=1>. Тесты: `pytest`.

## Установка на хостинг

1. Создайте бота в [@BotFather](https://t.me/BotFather), скопируйте токен.
2. Загрузите код **вне** веб-папки домена, например в `~/myapp`.
3. Настройте и установите:
   ```bash
   cd ~/myapp
   cp .env.example .env                              # BOT_TOKEN, PUBLIC_URL, ADMIN_IDS
   cp server/paths.conf.example server/paths.conf    # DATA_ROOT, PYTHON, PORT
   sh server/install.sh
   sh server/manage.sh start
   curl -s http://127.0.0.1:3090/health              # {"ok":true}
   ```
4. Положите `server/htaccess.example` в папку домена как `.htaccess` и укажите порт.
   Выпустите SSL-сертификат в панели: Mini App работает только по HTTPS.
5. Добавьте строки из `server/crontab.example` в cron.
6. Напишите боту `/start`.

## Частые проблемы

- **`/health` работает, а `/` отдаёт 404.** Apache переписывает `/` в `/index.php`;
  помогает `DirectoryIndex disabled`.
- **Каждые 5 минут "address already in use".** После перезагрузки остался старый PID-файл;
  `manage.sh` ищет процесс в `/proc`.
- **Telegram отвечает `409 Conflict`.** Запущены две копии бота.
- **После обновления видна старая версия.** Браузер Telegram кеширует файлы; статика отдаётся с `no-cache`.
- **В форме непонятная ошибка 422.** FastAPI считает пустое обязательное поле отсутствующим;
  используйте `Form("")` и свою проверку.
- **Порт занят чужим аккаунтом.** На одном сервере `127.0.0.1` может быть общим для аккаунтов —
  выбирайте редкий порт.

Лицензия: [MIT](../LICENSE).
