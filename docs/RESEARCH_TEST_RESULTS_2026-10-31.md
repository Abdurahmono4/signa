# GitHub ulanishlari: haqiqiy sinov natijalari

- 25 backend testi o‘tdi. Yangi testlar 6D row convention, identity/90°/180° aylanishlar, parallel vektorlarni rad etish, 53 → 133 joint mapping, tilni saqlash, noto‘g‘ri JSON, normalized input va qamrov ma’noga teng emasligini tekshiradi.
- Frontend TypeScript/Vite build o‘tdi. Alohida 3D chunk >500 kB ogohlantirishi saqlanadi.
- Mavjud Rocketbox playback regression testi o‘tdi: 28 kadr / 968 track, head/pelvis balandligi, rest pose va replay. Bu semantik baholash emas.
- `GET /api/research/sources`: 4 ta manba qaytdi.
- `GET /api/research/grammar`: HTTP 200, 158085 byte. Haqiqiy mahalliy How2Sign iboralari ishlatildi; LLM generatsiyasi ishga tushirilmadi.
- Brauzerda `Do not give 10 tablets.` va `Give 20 tablets.` solishtirildi: son va inkor o‘zgargani haqida ikki ogohlantirish, qamrov 0%/0%, asl matn o‘zgartirilmagani ko‘rsatildi. Bu faqat dasturiy test jumlalari.
- Brauzer file chooser orqali `backend/tests/fixtures/numeric-rotation-only.json` yuklandi. Bu 24 kadrli **sun’iy sonli aylanish testi**, haqiqiy ishora yoki ASL3DWord namunasi emas. Avatar ko‘rigi yuklandi, scrub va ijro ishladi, MP4 tugmasi o‘chdi: import joriy transkriptga bog‘lanmagan.
- Barcha matn manbalari NUL baytlarga tekshirildi. Ikki buzilgan frontend fayli tiklandi; avvalgi CSS build nusxasi `frontend/src/style.recovered.css`da saqlandi. `style.css` unga import qiladi, qo‘shimcha tadqiqot uslublari alohida qo‘shilgan.
- `/api/health`: ok=true, CPU, FFmpeg mavjud, tasdiqlangan o‘zbek ishoralari=0. Frontend ochildi.

Haqiqiy Dong checkpoint, ASL3DWord yoki SignAvatars 3D annotatsiyasi bilan sinov qilinmadi: bu aktivlar hali olinmagan. Sonli fixture bilan ishlash haqiqiy til ijrosi ishlayotganini anglatmaydi. Hech qanday yangi ML modeli o‘qitilmadi. Oldingi MaDiS/Rocketbox MP4 sinovi haqidagi natijalar alohida `TEST_RESULTS.md`da.

Manbalar tahlili va import formatlari: [RESEARCH_SOURCES.md](RESEARCH_SOURCES.md).
