# SignBridge UZ

Inglizcha audio/video → vaqtli matn → tajribaviy ASL avatar ijrosi → H.264/AAC MP4. Mahalliy CPU prototipi; React/TypeScript/Vite/R3F, FastAPI, Faster-Whisper small INT8, MaDiS, SQLite va FFmpeg ishlatiladi.

Oddiy interfeys: **Video yoki audio yuklash → avatar ijrosini ko‘rish → MP4 tayyorlash → yuklab olish**. Asosiy video chapda, hozirgi Rocketbox ayol avatari o‘ngda; audio natijasida avatar markazda. Ichki dataset sonlari va tadqiqot boshqaruvlari oddiy sahifada yo‘q.

Model bir iborani qabul qilmasa, o‘sha iboraning matni/subtitri saqlanadi va qisman natija deb ko‘rsatiladi. Bu tasdiqlangan yoki xatosiz ASL tarjimasi emas. Model qo‘l/yuz mosligi va tushunarlilik uchun kar foydalanuvchilar hamda ASL mutaxassisi bahosini talab qiladi. O‘zbekiston imo-ishora tili ushbu rejim emas.

## Ishga tushirish

```powershell
Set-Location D:\SignBridge-UZ
.\start.bat
```

Frontend: http://127.0.0.1:5174/ · API: http://127.0.0.1:8001/docs . Brauzerda 3D MP4 kadrlari olinayotganda oynani ochiq saqlang. Model CPUda vaqt oladi; nusxa yuklamang, jarayon holatini kuting. Original audio AACga qayta kodlanadi; harakatga vaqt yetmasa audio/video birga sekinlashtirilishi mumkin. Ishlar va tayyor eksportlar lokal storage ichida saqlanadi.

Python 3.11 `.venv`, Node va frontend dependencies kerak. FFmpeg/FFprobe `tools` yoki PATH ichida. MaDiS alohida CPU runtime hamda model assetlariga tayangan; `GET /api/neural/health` tayyorlikni ko‘rsatadi. Hozirgi lokal MaDiS manzili `.env.example`/`backend/app/neural_api.py` dagi SIGNBRIDGE_MADIS_BACKEND orqali sozlanadi. Loyiha boshqa kompyuterga ko‘chirilganda model fayllari alohida kerak.

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location frontend
npm.cmd ci
npm.cmd run build
Set-Location ..
.\.venv\Scripts\python.exe scripts\check-local-readiness.py
```

## Holat va sinovlar

2026-11-02: 117 backend testi, frontend build va frontend flow guard tekshiruvlari o‘tgan. Haqiqiy qisqa audio/video ASR va 3D MP4 eksportlari oldingi bosqichlarda tekshirilgan. Dastlab qisman rejada 6/7 ibora yaratildi; keyingi terminal tinish belgisi tuzatishidan so‘ng ayni haqiqiy videoda 7/7 ibora generatsiyasi o‘tdi. Asl transkript o‘zgarmadi; yangi uzun 3D browser MP4 eksporti hali sinovdan o‘tmagan. Sabab: docs/MODEL_TEXT_INPUT.md.

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
node --experimental-strip-types scripts\check-flow-guards.mjs
```

[Avatar va eksport sifati](docs/OUTPUT_QUALITY.md) · [Amaldagi holat](docs/CURRENT_STATUS.md) · [Qisman natija](docs/PARTIAL_MOTION.md) · [Train yaxlitligi](docs/TRAIN_INTEGRITY.md) · [Validation/test](docs/EVALUATION_DATA.md) · [Sinovlar](docs/TEST_RESULTS.md).

## Datasetlar va cheklovlar

How2Sign — ASL ma’lumotlari. Qidiruvda manba iborasiga aynan mos yozuvlar olinadi; test split model fit yoki qidiruvga qo‘shilmagan. Train RGB ZIPlarda CRC xatolari topilib, kuzatilgan 6 frontal klip qidiruvdan chiqarilgan. Train 2D gzipda dekompressiya xatosi bor va to‘liq o‘qitishga tayyor emas. Original arxivlar saqlangan. Model shu lokal datasetlarda qayta o‘qitilmadi.

Kod/GitHubga katta dataset, model vaznlari, `.venv`, user media yoki storage qo‘shilmasin; `.gitignore` mavjud. Bu bir foydalanuvchili lokal dastur, ommaviy server uchun autentifikatsiya va ko‘p foydalanuvchili navbat alohida ishdir.

How2Sign metadata CC BY-NC 4.0, MaDiS model CC BY-NC-ND 4.0, Rocketbox avatar MIT litsenziyalari qayd etilgan. Tijorat foydalanish huquqlari alohida hal qilinishi kerak. Manba/asset tafsilotlari [avatar pipeline](docs/AVATAR_PIPELINE.md) va [datasets](docs/DATASETS.md) hujjatlarida.

Har bir avatar ishida hozir 75 tagacha mos motion bo‘lagi / 30000 harakat kadri chegarasi bor. Bundan katta ish hisoblash oldidan aniq xabar bilan rad etiladi. Eksportdan oldin disk joyi ham tekshiriladi; bu boshqa dasturlar uchun disk rezervatsiyasi emas.
