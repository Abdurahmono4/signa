# Signa — ovozni ko‘ring

Inglizcha video yoki audio yuklang va **Imo-ishorada ijro etish** tugmasini bosing. Whisper nutqni matnga aylantiradi, **MaDiS-How2Sign** neyron modeli gaplardan uzluksiz tana va qo‘l harakatini yaratadi. Avatar media oynasining burchagida ko‘rinadi. Hisoblash ushbu kompyuterda bajariladi.

Bu tadqiqot prototipi: modelning ASL ma’nosi va tushunarliligi mutaxassislar bilan hali baholanmagan. SMPL-X harakatini mavjud CC0 avatarga ko‘chirish taxminiy; asl modelning qo‘l bazaviy shakli va yuz ifodalarining to‘liq mosligi tasdiqlanmagan. Eski 24 so‘zli lug‘at va 26 harf API darajasida saqlangan, asosiy sahifa esa neyron modeldan foydalanadi. Tafsilotlar: [NEURAL-MODEL.md](docs/NEURAL-MODEL.md).

## Ishga tushirish — Windows / VS Code

`Signa.code-workspace` faylini VS Code bilan oching. Loyiha papkasidagi terminalda:

```powershell
npm.cmd start
```

[Interfeys](http://127.0.0.1:5173) · [API hujjatlari](http://127.0.0.1:8000/docs). To‘xtatish: Ctrl+C.

Yangi kompyuterda Node.js 22+ va Python 3.12 bilan:

```powershell
npm.cmd run setup
npm.cmd run model
powershell -ExecutionPolicy Bypass -File scripts/setup-neural-model.ps1
npm.cmd start
```

Python topilmasa: `scripts/setup.ps1 -Python C:\Python312\python.exe`. Bevosita TypeScript manbasini o‘qiydigan Node sinovlari uchun Node.js 24 ishlatilgan.

Model skripti `small.en` va `medium.en` modellarini bir marta yuklaydi. Sahifa `balanced` / `small.en` rejimini avtomatik tanlaydi. Nutq CPU INT8 orqali mahalliy qayta ishlanadi; media tashqi AI xizmatiga yuborilmaydi.

Neyron ASL modeli alohida Python 3.11 muhitida ishlaydi. Asosiy checkpoint va Qwen fayllari taxminan 7.2 GB; CPU Torch va kutubxonalar uchun qo‘shimcha joy kerak. MaDiS kodi va vaznlari CC-BY-NC-ND-4.0 shartlarida, tadqiqot uchun olingan. Ular manba ZIP paketiga kiritilmaydi. NVIDIA GPU shart emas, ammo CPU’da tayyorlash video davomiyligidan uzoqroq bo‘lishi mumkin.

## Foydalanish

1. **Fayl tanlash** orqali video/audio yuklang yoki faylni studiya ustiga tashlang. MP4, MOV, WEBM, MP3, WAV, M4A, OGG va FLAC; 100 MB va 20 daqiqagacha.
2. **Imo-ishorada ijro etish**ni bosing. Nutq aniqlanadi, harakatlar tayyorlanadi va ijro avtomatik boshlanadi. Tayyorlashni **Bekor qilish** bilan to‘xtatish mumkin.
3. Media, gap subtitri va burchakdagi avatarni kuzating. Gap harakati ko‘pi bilan 1.25× tezlikda ijro etiladi. Harakat nutq vaqtidan uzun bo‘lsa, media ishora tugashini kutadi. So‘z va ishora vaqti taxminiy moslanadi.
4. Shu tugma bilan **Pauza** yoki **Qayta ijro etish**ni tanlang. Vaqt slayderi ikkala panelni birga boshqaradi. Boshidan boshlash, subtitr, ovoz va to‘liq ekran boshqaruvlari shu yerda.
5. **Boshqa fayl** bilan yangi media tanlang. Yangi fayl oldingi ijroni to‘xtatadi.

Asosiy sahifa noma’lum so‘zlarni harflab ijro etmaydi. Harakat yaratish muvaffaqiyatsiz bo‘lsa, xato ko‘rsatiladi va harakatsiz avatarli tarjima tayyor deb belgilanmaydi. Nutq matni noto‘g‘ri aniqlansa, ishora mazmuni ham noto‘g‘ri bo‘lishi mumkin; mavjud transkriptni API orqali tahrirlash mumkin.

## Avatarli video olish

Ijro tayyor bo‘lgach **Avatarli video tayyorlash**ni bosing. Dastur boshidan ijro qilib, original video ustiga burchakdagi avatar va joriy subtitrni birlashtiradi. Audio fayl uchun fonli avatar videosi yaratiladi. Yozuv tugagach **Videoni yuklab olish** bilan `.webm` faylni saqlang. Bu MP4 eksporti emas.

Yozish brauzerda, haqiqiy ijro tezligida bajariladi: tugaguncha sahifani ochiq qoldiring. **Bekor qilish** yozuvni to‘xtatadi. Chiqishning uzun tomoni ko‘pi bilan 1280 piksel, yozuvning hajm chegarasi 256 MB. Brauzer WebM yozishni qo‘llashi kerak. Media tashqi serverga yuborilmaydi.

Faqat muvaffaqiyatli yaratilgan avatar harakati eksport qilinadi. Modelning texnik ishlashi ASL mazmuni mutaxassis tasdig‘idan o‘tganini anglatmaydi.

Haqiqiy brauzerda avatarli VP9/Opus WebM yozildi, yuklab olindi va video/ovoz yo‘laklari PyAV bilan tekshirildi. Shu sinovdan keyingi audio vaqt tuzatishi va yangi yaqin kameraning qayta brauzer yozuvi hali tekshirilmagan; aniq natijalar va cheklovlar [VALIDATION.md](docs/VALIDATION.md) da qayd etilgan.

Shu brauzer tabida sahifa yangilansa, oxirgi ish/fayl sessiyadan tiklanadi; ijro o‘z-o‘zidan boshlanmaydi. **Imo-ishorada ijro etish** bilan davom eting. Bu ko‘p foydalanuvchilik hisob yoki doimiy foydalanuvchi kutubxonasi emas.

Yuklashdan oldingi **Namunani sinash** ham haqiqiy yuklash → ASR → avatar zanjiridan o‘tadi; tayyor matn bilan ASRni chetlab o‘tmaydi. `examples/education-demo.mp4` — qisqa sintetik inglizcha nazorat videosi; `examples/long-speech-demo.*` — uzunroq sintetik audio va tayanch matn.

Sahifa bitta studiyadan iborat. Eski laboratoriya, qamrov ro‘yxati, kutubxona va tahrir panellari asosiy interfeysda ko‘rsatilmaydi. Tarix, tahrir, eksport va korpus tekshiruvi API qatlamida saqlangan.

## Avatar va ijro

Avatar yangi soch, ko‘zoynak, yuz shakli va keng indigo kiyim bilan qayta bezatilgan. Manba modelning qo‘l/barmoq skeleti va yuz animatsiya kanallari saqlangan. Harakatlar [Studio Galt manba arxivi](https://github.com/StudioGalt/Sign-Language-Mocap-Archive) dan olingan; manifestda manba URL, Git blob SHA va CC0-1.0 litsenziyasi qayd etilgan.

Neyron ijro 133 o‘lchamli, 24 fps tana/qo‘l aylanishlaridan yaratiladi. Harakatlar tekshiriladi va barcha kadrlar saqlanadi; noma’lum so‘z o‘rniga tasodifiy lug‘at ishorasi qo‘yilmaydi. Model yaratgan harakatning lingvistik sifati alohida baholanishi kerak. Eski korpus kliplari tajriba va regressiya tekshiruvlari uchun saqlangan.

## Tekshirish

```powershell
npm.cmd test
npm.cmd run build
node scripts/test-avatar.mjs
node scripts/test-interpreter.mjs
node scripts/test-playback.mjs
node scripts/test-playback-media.mjs
node scripts/test-framing.mjs
node scripts/test-composite-export.mjs
node scripts/test-neural-motion.mjs
```

Sinovlar va brauzer kuzatuvlari: [VALIDATION.md](docs/VALIDATION.md). Interfeysni qabul qilish qadamlari: [UI_REDESIGN.md](docs/UI_REDESIGN.md). Arxitektura: [ARCHITECTURE.md](docs/ARCHITECTURE.md). Avatar/korpus: [AVATAR.md](docs/AVATAR.md). Hali zarur ilmiy bosqichlar: [RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md).

## Fayllar va chegaralar

- `frontend/src/main.tsx`, `style.css`: yagona media/avatar sahifasi.
- `frontend/src/playback.ts`, `useInterpreterPlayback.ts`: umumiy ijro vaqti, media pauzalari va seek.
- `frontend/src/Avatar3D.tsx`, `interpreter.ts`: 3D ijro va avatar bezagi.
- `frontend/src/neuralMotion.ts`: MaDiS aylanishlarini avatar skeletiga ko‘chirish.
- `frontend/src/compositeExport.ts`: burchakdagi avatarli canvas, audio va WebM yozuvi.
- `backend/app/asr.py`: dekodlash, nutq bo‘laklari, so‘zlar va audit.
- `backend/app/main.py`, `signs.py`: API, SQLite, korpus va ijro rejasi.
- `backend/app/neural.py`, `inference/madis_runner.py`: alohida CPU model jarayoni, navbat, bekor qilish va natija keshi.
- `backend/data/`: mahalliy media/baza; `backend/models/`: modellar.

Bir foydalanuvchilik mahalliy dastur; hisoblash ishlari umumiy navbat bilan bajariladi. Serverlar `127.0.0.1` bilan cheklangan. Server to‘xtasa, tugallanmagan ish qayta boshlanadi. Hisoblar, ijtimoiy tarmoq havolasidan import va ovozsiz video sahnalarini tushunish yo‘q. Ayrim MOV kodeklari brauzerda ochilmasligi mumkin. Haqiqiy ASL foydalanuvchilari bilan baholash hali bajarilmagan.

Model manbalari: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [medium.en](https://huggingface.co/Systran/faster-whisper-medium.en), [small.en](https://huggingface.co/Systran/faster-whisper-small.en).
