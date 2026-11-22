# Tarjima chegaralari

Amaldagi asosiy yo‘nalish inglizcha nutq → tajribaviy ASL. ASL O‘zbekiston imo-ishora tili emas. Whisper small/CPU vaqtli transkript beradi; xatolar, shovqin, aksentlar va terminlar mustaqil reference transkriptlar bilan baholanishi kerak. To‘liq raqamli sukunat rad etiladi; bu har qanday shovqin/musiqada gallyutsinatsiya bo‘lmasligi kafolati emas.

Ikki backend yo‘li bor: How2Sign yozuvlarini aynan butun ibora bo‘yicha qidirish va pretrained MaDiS generatsiyasi. Qidiruvdagi qamrov tarjima aniqligini bildirmaydi. ASL grammatikasini so‘zma-so‘z o‘ylab topish yoki boshqa til ishoralarini jim qo‘shish yo‘q.

MaDiS kirish lug‘atiga mos bo‘lishi sifatli ishora hosil bo‘lishini isbotlamaydi. Faqat oldindan aniqlangan unsupported chunklar qisman rejada matn/subtitr intervali bo‘lib qoladi. Qo‘llanadigan chunkda yaroqsiz model chiqishi hali aniq xato sifatida to‘xtaydi. Generatsiya/retarget eksperimenti mutaxassis tasdiqlagan tarjima deb belgilanmaydi.

Rocketbox skeletga SMPL-X aylanishlari taxminiy moslashtiriladi. Litsenziyalangan SMPL-X hand-mean va tekshirilgan ASL yuz grammatikasi yo‘q. Gaps neytral holat va silliq o‘tish bilan beriladi, faol sign kadrlar o‘zgartirilmaydi. Original media vaqtiga moslik taxminiy; harakat tezligini oshirmaslik uchun media global sekinlashtirilishi mumkin.

Ilmiy baholash: reference inglizcha transkriptlarda WER/deletions, so‘z vaqti xatosi, matn→ishora ma’no to‘g‘riligi, kar foydalanuvchilarning tushunishi, ikki mustaqil ASL ekspertining qo‘l/yuz bahosi, CPU/RAM/kechikish o‘lchovlari. Test mustaqil qoladi. Train arxivlaridagi xatolar to‘liq model fitdan oldin tuzatilishi kerak. Batafsil PARTIAL_MOTION.md va TRAIN_INTEGRITY.md.
