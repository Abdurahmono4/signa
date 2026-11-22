# To‘rtta GitHub manbasi: tekshiruv va amaliy ulanish

Tekshirilgan sana: 2026-10-31. Manbalar rasmiy GitHub fayllari orqali o‘qildi. Quyidagi commitlar qayd etildi. Katta dataset, model vaznlari yoki CUDA muhiti o‘rnatilmadi.

| Manba | Commit | Bizda ishlatilgan qism | Hali mavjud emas |
|---|---|---|---|
| [constrained-translation-sign-avatar](https://github.com/ntantaroudas/constrained-translation-sign-avatar) | 457e46fbbc9b7c775b44fee8f3fa1041d61399df | MIT `gbnf.py` radix-tree grammatika generatori; faol How2Sign **to‘liq iboralari** uchun grammatika; asl/taklif matn qamrovini solishtirish | EuroLLM, NLLB va semantik baholash modellari ishga tushirilmagan |
| [Dong SignAvatar](https://github.com/dongludeeplearning/SignAvatar) | 1fe3dedc446b4b6eb7ef7af57fc318250cf213c0 | Hujjatlashtirilgan 53 bo‘g‘im × 6D aylanish formati uchun mustaqil matematik JSON adapter; mavjud Rocketbox oynasida ko‘rik | ASL3DWord, checkpoint va litsenziyali SMPL-X aktivlari |
| [Sign-Kit](https://github.com/spectre900/Sign-Kit-An-Avatar-based-ISL-Toolkit) | cbb3491d2514b1b908658808cfffb497d020ff9d | React/Three.js boshqaruvi, ijro navbati va tezlik/pauza yondashuvi o‘rganildi. Bizning vaqtga bog‘langan tezlik boshqaruvimiz mustaqil yozildi | ISL ishoralari va XBOT/YBOT aktivlari ko‘chirilmagan |
| [ZhengdiYu SignAvatars](https://github.com/ZhengdiYu/SignAvatars) | bbfb35056aaad252ae67c60b44eb91618506d4a8 | Oldingi metadata bog‘lanishi va 182 → 133 adapter; endi JSON API va avatar ko‘rigiga ulandi | Ruxsatli 3D annotatsiyalar, hand mean va yuz grammatikasi moslashuvi |

## Muhim farqlar

- Birinchi repo International Sign lug‘ati ustida **matnni qayta yozish tadqiqoti**. Tayyor 3D ayol modeli yoki uning harakat kliplari berilmaydi. Biz IS glossalarini ASL lug‘atiga qo‘shmadik.
- Dong SignAvatar so‘z darajasidagi transformer/CVAE modelidir. Repodagi `checkpoints` papkasida log/YAML mavjud; og‘irliklar alohida so‘raladi. Uni hozir ishlayotgan MaDiS o‘rniga yashirin almashtirmadik. Kod litsenziyasi CC BY-NC 4.0; tijoriy foydalanish uchun alohida ruxsat kerak.
- Sign-Kit hind imo-ishora tili uchun 26 harf va 4 so‘z (`HOME`, `PERSON`, `TIME`, `YOU`) animatsiyasini saqlaydi. Ular ASL yoki O‘zbekiston ishoralari emas. Rootda litsenziya fayli topilmadi. Biz uning kodini yoki GLB aktivlarini runtimega nusxalamadik.
- SignAvatars tayyor universal matndan tarjimon emas; 3D dataset va vizualizatsiya vositalaridir. Viewer GPL-3.0, dataset notijoriy ruxsat, SMPL-X aktivlari alohida shartlarga ega.

## Platformadagi vositalar

`Yangi ayol modeli` oynasida `GitHub manbalari va tadqiqot vositalari` bo‘limi bor:

1. Har bir manbaning tili, litsenziyasi, haqiqiy ulanishi va yetishmayotgan aktivlari.
2. Ruxsatli, oldindan JSONga chiqarilgan **bitta klipni** import qilish va Rocketboxda texnik ko‘rish. PKL/pickle bajarilmaydi. Import avtomatik joriy nutqqa bog‘lanmaydi yoki tarjima deb eksport qilinmaydi.
3. Asl inglizcha matn va qo‘lda taklif etilgan variant qamrovini solishtirish. Son/inkor o‘zgarishi alohida qayd etiladi. Ma’no modeli yo‘q, shuning uchun `meaning_verified=false`, `applied=false`.
4. Faol, rad etilmagan to‘liq How2Sign iboralari uchun GBNF fayl. Bu generator matn yaratmaydi; keyingi llama.cpp tajribasiga tayyor interfeys. Lug‘at cheklovi tarjimaning ma’nosini kafolatlamaydi.
5. Ko‘rik tezligi 0.5–1.5×: media va avatar bir vaqt manbaidan ishlaydi. Bu sozlama eksport vaqtlarini o‘zgartirmaydi.

## JSON formatlar

Dong SignAvatar ning `blender_format.py` va generation kodi joint tartibini belgilaydi: root, 21 body, 15 left hand, 15 right hand, jaw. Upstream 3×classes×53×T×6 natijadan avval kerakli bitta klipni ajratib, T×53×6 qilib JSONga chiqaring:

```json
{"format":"signavatar-rot6d-53","normalized":false,"fps":30,"name":"Klip nomi","frames":[]}
```

Bo‘sh massiv misol sxemasi; haqiqiy import 1–3000 kadr talab qiladi. PyTorch3D 6D row convention qo‘llanadi. Nolinchi yoki parallel vektorlar rad etiladi. Natija 133 kanalli axis-angle oqimga o‘tadi. Expression manbada yo‘q: nol bilan to‘ldiriladi va bu cheklov qaytariladi.

SignAvatars:

```json
{"fps":24,"language":"asl","smplx":[],"total_valid_index":[]}
```

Har bir haqiqiy `smplx` qatori 182 chekli son bo‘lishi kerak. `language` talab qilinadi: `asl`, `dgs`, `isl`, `uz_sign` yoki `other`. Bu foydalanuvchi ko‘rsatgan til, mustaqil tasdiq emas. Uzilgan kadr indekslari vaqtni yashirin siqmasdan rad etiladi. Brauzer ko‘rigi 10 000 kadr, so‘rov 16 MB bilan chegaralangan.

## API

- `GET /api/research/sources`
- `GET /api/research/grammar`
- `POST /api/research/audit` — `{original, candidate}`
- `POST /api/research/motions/convert` — yuqoridagi JSONlardan biri

Asosiy fayllar: `backend/app/research_api.py`, `research_motion.py`, `vendor/constrained_gbnf.py`, `frontend/src/ResearchTools.tsx`.

MIT litsenziya `backend/app/vendor/CONSTRAINED_LICENSE`da saqlandi. O‘qilgan manbalar snapshotlari `docs/research/upstream/`da; ular asosiy server orqali tarqatilmaydi. Runtimega faqat MIT grammatika moduli nusxalangan; qolgan adapterlar mustaqil yozilgan.

## Keyingi ilmiy ish

Rasmiy annotatsiya/checkpointlarni olish, alohida test to‘plamini ajratish, WER hamda semantik saqlanishni baholash, ASL mutaxassislari bilan qo‘l shakli/bilak/yuz grammatikasini tekshirish. Hozirgi numeric testlar til aniqligini isbotlamaydi.
