# tg-miniapp-starter (o'zbekcha)

Telegram bot va Telegram Mini App uchun tayyor shablon. U **oddiy, arzon hostingda** ishlaydi:
Docker, root huquqi, systemd va ochiq port kerak emas. Hostingingizda SSH, SSL'li domen,
cron va Python 3.11 bo'lsa, shu yetarli.

## Ichida nima bor

- **Bitta jarayon** ham botni (aiogram 3), ham veb qismni (FastAPI) ishlatadi.
- **Parolsiz kirish**: Telegram yuboradigan `initData` bot tokeni bilan tekshiriladi.
- **Kameradan rasm**: ilova telefon kamerasini to'g'ridan-to'g'ri ochadi, rasmni yuklashdan oldin
  kichraytiradi, server esa burchagiga sana va vaqtni yozadi.
- **Yopiq rasm havolalari**: rasmlar veb papkadan tashqarida, har bir havola imzolangan.
- **Excel eksport**: jonli `SUM` formulasi va rasmlarning kichik nusxalari bilan.
  Admin botga `/export` yozib oladi.
- **Hosting skriptlari**: o'rnatish, ishga tushirish/to'xtatish, ikkinchi nusxa ochmaydigan qarovul,
  kunlik zaxira, Apache `.htaccess` orqali proxy.

## Lokal ishga tushirish

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: . .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env          # lokal sinov uchun DEV_MODE=1 qiling
uvicorn app.main:app --port 8000
```

Brauzerda <http://localhost:8000/?dev=1> ni oching. Testlar: `pytest`.

## Hostingga qo'yish

1. [@BotFather](https://t.me/BotFather) da bot yarating, tokenni oling.
2. Kodni domen papkasidan **tashqariga** yuklang, masalan `~/myapp`.
3. Sozlang va o'rnating:
   ```bash
   cd ~/myapp
   cp .env.example .env                              # BOT_TOKEN, PUBLIC_URL, ADMIN_IDS
   cp server/paths.conf.example server/paths.conf    # DATA_ROOT, PYTHON, PORT
   sh server/install.sh
   sh server/manage.sh start
   curl -s http://127.0.0.1:3090/health              # {"ok":true}
   ```
4. `server/htaccess.example` ni domen papkasiga `.htaccess` nomi bilan qo'ying va portni yozing.
   Panelda SSL sertifikat oling: Mini App faqat HTTPS bilan ishlaydi.
5. `server/crontab.example` dagi qatorlarni cron'ga qo'shing.
6. Telegram'da botingizga `/start` yozing.

## Ko'p uchraydigan muammolar

- **`/health` ishlaydi, `/` esa 404 beradi.** Apache `/` ni `/index.php` ga burib yuboradi,
  `.htaccess` dagi `DirectoryIndex disabled` qatori buni to'xtatadi.
- **Har 5 daqiqada "address already in use" chiqadi.** Server qayta yonganda eski PID fayl qolib ketgan.
  `manage.sh` jarayonni PID fayl bo'yicha emas, `/proc` dan qidiradi.
- **Telegram `409 Conflict` qaytaradi.** Bot ikki nusxada ishlayapti, `manage.sh` buni oldini oladi.
- **Yangilanishdan keyin ham eski ko'rinish chiqadi.** Telegram brauzeri fayllarni keshlaydi.
  Fayllar `no-cache` bilan beriladi.
- **Formada tushunarsiz "422" xatosi chiqadi.** FastAPI bo'sh majburiy maydonni "yo'q" deb hisoblaydi.
  Maydonni `Form("")` qilib, tekshiruvni o'zimiz yozamiz.
- **Boshqa akkauntning xizmatiga ulanib qolasiz.** Bitta serverda `127.0.0.1` portlari akkauntlar
  orasida umumiy bo'lishi mumkin, shuning uchun noyob port tanlang.

Litsenziya: [MIT](../LICENSE).
