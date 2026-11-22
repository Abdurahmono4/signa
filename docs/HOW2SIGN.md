# How2Sign kichik to‘plam integratsiyasi

## Haqiqiy ZIP bilan bajarilgan sinov — 2026-10-28

`val_rgb_front_clips.zip` topildi: 1,778,074,855 bayt. Importer 30 ta real ASL klipni original CSV bilan bog‘ladi. Kliplar `datasets/how2sign/clips` ichida, manba va litsenziya `catalog.json` da. Hech biri mustaqil lingvistik tekshiruvdan o‘tgan deb belgilanmadi.

Windows System.Speech yordamida **At least in a physical way.** jumlasining sintetik inglizcha audiosi yaratildi. Bu inson yozgan tabiiy nutq namunasi emas. `examples/how2sign-speech.mp4` shu audiodan tuzilgan nazorat videosi. U brauzer Fayl tanlash orqali haqiqiy upload va Whisper tiny/en oqimidan o‘tdi. Natija **at least in a physical way.** bo‘ldi. Katalog iborasi aniq moslandi (shu jumla uchun qamrov 100%; erkin matn aniqligi o‘lchovi emas).

Brauzerdagi HumanSigner haqiqiy manba klipini seek qilib PNG kadrlarni yaratdi va serverga yubordi. Yashil fonni tozalash va markazdagi tarjimonni kattalashtirish yaxshilandi. FFmpeg yonma-yon original video + tarjimon + subtitr MP4 ni yaratdi. FFprobe: **H.264 + AAC, 1280×720, 2.239093 soniya**. Natijadan 0.6 soniyadagi kadr olinib vizual tekshirildi: asl video chapda, haqiqiy inson tarjimon o‘ngda, qora fon, subtitr pastda.

Natija: `examples/how2sign-result.mp4`; HTTP download endpointdan alohida saqlangan nusxa: `examples/how2sign-download.mp4`. Natija rasmi: `docs/how2sign-result-frame.png`. Ish ID: `LOCAL_ID`. IAB vositasining download hodisasini kutishida timeout bo‘ldi; server download endpointi orqali haqiqiy MP4 alohida yuklab olindi. Bu tafovut yashirilmadi.

Frontend build va 9 backend testi o‘tdi. Boshqa 29 klipning lingvistik ma’nosi, barcha qo‘l chegaralari va yashil rangli kiyimlarda chroma-key holati hali alohida baholanmagan. Birinchi qayta eksport kadr sessiyasi frontend HMR yangilanishi sabab uzildi; sessiya bekor qilinib, yangi eksport muvaffaqiyatli tugadi. Sahifa yangilanganda oxirgi ish tiklanadi, tugallanmagan kadr sessiyasini Bekor qilish orqali qayta boshlash mumkin.

## Yuklash va import

`datasets/how2sign/how2sign_val.csv` rasmiy Google Drive manbasidan olindi (311131 bayt). Bu original Validation metadata; manually re-aligned metadata bilan almashtirmang.

`val_rgb_front_clips.zip` faylini `D:\SignBridge-UZ\datasets\how2sign` yoki foydalanuvchining `Downloads` papkasida saqlang. Server har 15 soniyada shu nomli tugallangan ZIP ni tekshiradi. `.crdownload` fayllari ochilmaydi. Arxivdan hamma fayllar ochilmaydi: 2–12 soniyali dastlabki 30 tagacha mos metadata klipi tanlanadi, FFprobe bilan ochilishi tekshiriladi. Kliplar 30 MB dan oshmasin. Arxiv yo‘llari bo‘yicha extraction yo‘q; boshqariladigan hash nomlar bilan lokal klip papkasiga yoziladi. Metadata CSV, litsenziya va manba saqlanadi.

`GET /api/how2sign`: holat va kliplar. `GET /api/how2sign/clips/{id}`: faqat katalogdagi klip. Original ZIP/fayllar o‘chirilmaydi.

## Ijro

Sozlamada Inglizcha → ASL manba videolari tanlangan. Whisper tiny tez boshlash uchun default, small aniqlik uchun tanlanishi mumkin. Til `en`; kirish o‘zbekcha bo‘lsa Sozlamada `uz` tanlang.

Katalogdagi ibora tugmasi uni Matn rejimiga qo‘yadi. “Ishoralarni tekshirish” bilan klip o‘z tabiiy vaqtida ochiladi. Media yuklanganda ASR vaqtli so‘zlari ketma-ket moslashtiriladi, shuning uchun ibora ikki ASR segmentiga ajralganda ham moslik topilishi mumkin. Faqat butun katalog iborasi: fuzzy/semantik taxminiy almashtirish yo‘q. Media rejimida klip tezligi 0.5–2× diapazonga mos kelmasa subtitr fallback. Matn preview qamrovi manba gapiga moslik, lingvistik aniqlik bahosi emas.

Inson tarjimon videosi HTML video bilan ko‘rsatiladi; 3D avatar deb belgilanmaydi. “3D harakatni sinash” alohida eski texnik demo. MP4 eksportida mos klip seek qilinib 384×512 PNG kadrlar olinadi, kuchli yashil fon olib tashlanadi, FFmpeg bilan qora o‘ng panelga qo‘yiladi. Mos tarjima yo‘q oraliqlarda tarjimon paneli bo‘sh; original audio va subtitr saqlanadi. Full-sentence generative tarjima modeli hozir bu oqimga ulanmagan.

## Tekshirish holati

2026-10-28: 9 backend testi va frontend build o‘tdi. Importer sintetik alohida video/metadata fixture bilan tekshirildi; u haqiqiy ASL yozuvi sifatida bazaga qo‘shilmadi. Haqiqiy How2Sign ZIP hali kelmagan paytda manba kliplari ijrosi, yashil fon qirqimi, timestamp alignment va browser eksporti tasdiqlanmadi. Haqiqiy kliplarga `verified=false` beriladi. Ularning ma’nosi va original vaqt mosligi mutaxassis ko‘rigini talab qiladi.

## Manbalar

- Dataset va litsenziya: https://how2sign.github.io/#download
- Frontal validation ZIP: https://drive.google.com/file/d/1DhLH8tIBn9HsTzUJUfsEOGcP4l9EvOiO/view
- Original validation matni: https://drive.google.com/file/d/1aBQUClTlZB504JtDISJ0DJlbuYUZCGu3/view

How2Sign ASL datasetidir, O‘zbekiston imo-ishora tili emas. CC BY-NC 4.0, tijoriy bo‘lmagan tadqiqot uchun. Datasetni platformada ishlatish avtomatik tijoriy ruxsat bermaydi. Manba va litsenziyani natijalar bilan saqlang. Ushbu kichik validation subset rivojlantirish uchun ishlatilganidan keyin mustaqil hold-out test sifatida baholanmasin.
