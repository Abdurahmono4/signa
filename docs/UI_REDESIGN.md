# Yagona sahifani qabul qilish

Asosiy oqim: **video/audio yuklash → “Imo-ishorada ijro etish” → media burchagida avatarni kuzatish → ixtiyoriy avatarli video olish**. Krem va binafsha rangli sahifada bitta studiya bor; laboratoriya, kutubxona, qamrov va tahrir menyulari asosiy oqimdan chiqarilgan.

Avatar yangi soch, ko‘zoynak, yuz va keng indigo kiyim bilan o‘zgartirilgan; yozilgan qo‘l/barmoq hamda yuz animatsiyasi saqlangan. Katta tugma tayyorlash, pauza va qayta ijroni boshqaradi. Standart tezkor so‘z rejimi lug‘at kliplarini ko‘pi bilan 1.25× ijro etadi; mos kelmagan so‘zlar qo‘shimcha pauzasiz vaqtli subtitrda qoladi. **Harflab ko‘rsatish** dastlab o‘chiq.

## Qayta tekshirish qadamlari

1. `npm.cmd start`; `http://127.0.0.1:5173` ni oching. Fayl tanlash maydoni, media/avatar panellari va **Imo-ishorada ijro etish** tugmasi borligini tekshiring.
2. **Namunani sinash**ni bosing. Yuklash va haqiqiy ASR tugagach ijro boshlanishi; Hello, Please, Book, My Name Is va Bye uchun avatar harakatini kuzating. Bu sintetik nazorat namunasidir.
3. **Pauza**ni bosing, kuting. Ikkala panelning umumiy vaqti o‘zgarmasligi kerak. Slayderni oldinga/orqaga suring; avatar kadr va media vaqti birga yangilanishini tekshiring.
4. Mos ishora nutqdagi vaqtdan uzun bo‘lsa, media uning tugashini kutishini tekshiring. Lug‘atda yo‘q so‘zlar uchun media to‘xtamasligi va so‘zma-so‘z subtitr o‘z vaqtida almashishi kerak.
5. Boshidan boshlash, subtitr, ovoz va to‘liq ekran tugmalarini tekshiring. Oxirida **Qayta ijro etish** qayta boshlashi kerak.
6. **Boshqa fayl** orqali `examples/education-demo.mp4` ni tanlang va asosiy tugmani bosing. Video chapda ko‘rinishi, Please/Book ishoralari va noma’lum so‘zlar uchun vaqtli subtitrni tekshiring. **Harflab ko‘rsatish** o‘chiqligida **HARFLAB** holati yoki harf sabab ortiqcha pauza bo‘lmasin. Barcha gapning grammatik ASL tarjimasi kutilmaydi.
7. Tayyorlashni **Bekor qilish** bilan to‘xtating, keyin qayta boshlang. Noto‘g‘ri format yoki 100 MB dan katta fayl uchun tushunarli xabar chiqishini tekshiring.
8. Tor va balandligi kichik oynada panellar, tugma va vaqt boshqaruvlariga yetish mumkinligini tekshiring.
9. Ixtiyoriy **Harflab ko‘rsatish**ni yoqing: noma’lum inglizcha ism/so‘z va takror harflarni tekshiring. **HARFLAB**, asl so‘z va joriy harf ko‘rinsin; media harflarni kutsin. Raqam yoki A–Z ga sig‘magan belgi bo‘lsa, butun so‘z subtitrda qoladi. Belgini o‘chirish tezkor so‘z rejimiga qaytarsin. Uzun harflash faqat shu ixtiyoriy rejimda ijroni ancha uzaytirishi kutiladi.
10. Fayl yuklangan tabni yangilang. Oxirgi ish/fayl qaytishi, ijro esa asosiy tugma bosilmaguncha boshlanmasligi kerak.
11. Mos ishorali media uchun **Avatarli video tayyorlash**ni bosing. Jarayon boshidan yozsin; asl video, burchakdagi harakatli avatar, ovoz va tanlangan subtitr chiqishda borligini tekshiring. Tayyor previewni va **Videoni yuklab olish**dan olingan WebM faylni mustaqil pleyerda oching. Ovoz oldin mute bo‘lsa ham faylda original ovoz borligi va eksportdan keyin avvalgi mute holati tiklanishini tekshiring.
12. Eksportni bekor qilish, so‘ng qayta boshlashni tekshiring. Yozuvda tabni yashirish tushunarli xabar bilan yozuvni to‘xtatsin. Nol harakatli rejada bo‘sh avatar videosi berilmasin; mos namuna yoki ixtiyoriy harflash yo‘li ko‘rsatilsin.

Ushbu ro‘yxat bajarilishi kerak bo‘lgan qabul qadamlari; har bir band o‘tkazilgan degani emas. Yangi WebM eksportining haqiqiy brauzer sinovi hozircha bajarilmagan. O‘tkazilgan tekshiruvlar [VALIDATION.md](VALIDATION.md) da. Bu ro‘yxatning o‘zi ixtiyoriy inglizcha gapning to‘liq ASL tarjimasi yoki ASL foydalanuvchilari tushunarliligini tasdiqlamaydi.
