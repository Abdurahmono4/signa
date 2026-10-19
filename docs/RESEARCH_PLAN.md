# Magistrlik ishini yakunlash rejasi

**Ishchi mavzu:** “Inglizcha audio va video kontentini ASL orqali taqdim etuvchi intellektual muhandislik platformasini ishlab chiqish va baholash”.

**Kelishilgan yo‘nalish:** kirish nutqi asosan inglizcha; chiqish tili Amerika imo-ishora tili — ASL. Interfeys o‘zbekcha bo‘lishi chiqish tili o‘zbek imo-ishora tili ekanini anglatmaydi. Mahalliy imo-ishora tiliga moslashtirish alohida hamkorlik va korpus talab qiladi.

Bu hujjat dasturdan baholangan ilmiy yechimga o‘tish rejasidir. Amaldagi interfeys yagona media/avatar sahifasiga qayta qurilgan: yuklash → ijro → media yonida ishora; texnik tekshiruvlar [VALIDATION.md](VALIDATION.md) da. Quyidagi sonli maqsadlar taklif etilgan qabul mezonlari; ular olingan ilmiy natijalar emas. Sinov boshlanishidan oldin ilmiy rahbar va ASL hamkorlari bilan mezonlar tasdiqlanadi.

## 1. Tadqiqot chegarasi va savollari

Magistrlik uchun birinchi tugallangan mahsulotni cheklangan ta’limiy sohadan boshlash maqsadga muvofiq: qisqa dars ko‘rsatmalari, tanishuv va o‘quv jarayonidagi xabarlar. Umumiy ma’ruza, film, qo‘shiq va ixtiyoriy gapni sifatli ASL ga o‘girish hozirgi kichik lug‘at korpusi bilan bajarilmaydi. Qo‘llab-quvvatlanmaydigan mazmun ochiq ko‘rsatilishi kerak.

Tadqiqot savollari:

1. To‘liq vaqt chizig‘i, ustma-ust kontekst va audit inglizcha nutqda tushib qolgan so‘zlar hamda segment chegarasi xatolariga qanday ta’sir qiladi?
2. Cheklangan soha uchun ekspert tekshirgan ASL gap animatsiyalari ma’noni foydalanuvchiga qanchalik yetkazadi?
3. Avatar eksporti, ijro tezligi va kliplararo o‘tishlar ishora tushunarliligiga qanday ta’sir qiladi?
4. Matn, lug‘at yordamchisi va gap darajasidagi ASL yechimlarining foydalanuvchi vazifasini bajarishdagi farqi qanday?

Hozirgi tizimning ilmiy tavsifi: **inson tekshiruvi, vaqtli nutq tahlili, bilimlar bazasiga tayangan ASL lug‘at yordami va ixtiyoriy A–Z barmoq alifbosini birlashtiruvchi muhandislik prototipi**. Korpusda 24 lug‘at klipi va 26 harf yozuvi bor. Standart tezkor so‘z rejimida noma’lum matn ortiqcha pauzasiz subtitrda qoladi; bu matnning ASL tarjimasi emas. Faqat foydalanuvchi yoqqan harflash so‘z yozilishini beradi; ASL gap grammatikasi yoki semantik tarjimani yaratmaydi. Yangi tarjima modeli yaratilgani yoki umumiy ASL tarjimoni tayyorligi hozir da’vo qilinmaydi.

## 2. Hozir bor va hali bajarilmagan qismlar

| Qism | Amaldagi holat | Tugallash uchun kerak |
|---|---|---|
| Media va saqlash | Mahalliy audio/video yuklash, 100 MB / 20 daqiqa, SQLite kutubxona | Tadqiqot namunalari manifesti, zaxira va takrorlanadigan ishga tushirish |
| Nutqni aniqlash | small.en / medium.en, vaqtli segmentlar, progress, bekor qilish | Belgilangan real inglizcha nutq korpusida WER va vaqt o‘lchovi |
| Sifat nazorati | Shubhali so‘z/oraliq, qayta tahlil, tahrir, tarix, eksport | Inson tayanch matni va xatolar tahlili |
| Lug‘at yordamchisi | Eng uzun ibora mosligi, tezkor so‘z rejimi, ixtiyoriy A–Z harflash, vaqt/rig holatlari, alohida lug‘at/harflash hisoblari | Kontekst va ASL gap grammatikasini hisobga oluvchi alohida modul |
| Avatar | Qayta bezatilgan Galtis GLB, qo‘l/barmoq/yuz tracklari, manifestdagi manba kliplar, media pauzali umumiy ijro | Manba bilan eksport taqqoslash, tabiiy o‘tishlar va lingvistik tekshiruv |
| Ekspert tekshiruvi | draft/approved/rejected, ism va izoh | Haqiqiy ASL mutaxassislari bilan yozma protokol; mustaqil baholash |
| Gap darajasidagi tarjima | Hali yo‘q | Tanlangan sohada parallel English→ASL gap korpusi va tarjima/retrieval qatlami |
| Foydalanuvchi tajribasi | Bitta sahifada yuklash, aniq ijro tugmasi, yonma-yon media va avatar | Kar va zaif eshituvchi ASL foydalanuvchilari bilan tushunarlilik/vazifa tajribasi |

Qamrov foizi faqat ijro qilinadigan lug‘at tokenlarini bildiradi. Unga tasdiqlanmagan manba previewlari ham kirishi mumkin. Bu ko‘rsatkich ASL tarjima aniqligi bilan almashtirilmaydi. Testlarda ishlatilgan “approved” sun’iy fixturelar haqiqiy ekspert tasdig‘i emas.

## 3. Intellektual muhandislik arxitekturasi

Tizimning kuzatiladigan zanjiri: **signal → nutq modeli → vaqtli matn → bilimlar bazasi va qaror qoidalari → harakat rejasi → avatar → inson bahosi**. Har qatlam kirish/chiqish va xatolarini saqlaydi. Nutq sifati, lug‘at qamrovi, animatsiya texnik sifati va ma’no tushunarliligi alohida o‘lchanadi.

Keyingi gap darajasidagi modul uchun avval ekspert tasdiqlagan yopiq gaplar to‘plamini qo‘llash mumkin: inglizcha gap/niyat → tekshirilgan ASL ijrosi. Matn qo‘llab-quvvatlanadigan niyatga ishonchli mos kelmasa, tizim subtitr va tekshiruv holatini qaytaradi. Bu cheklangan sohadagi yechim sifatida nomlanadi. Keyin yangi iboralarga umumlashtirish zarurati va ma’lumot yetarliligi tekshirilgandan so‘ng o‘rgatiladigan model tanlanadi. Hozirgi loyihada bunday gap qatlami ham, modelni o‘qitish jarayoni ham mavjud emas.

Gap tarjimasida shunchaki inglizcha so‘zlar tartibini ishoralarga almashtirish yetarli deb qabul qilinmaydi. ASL ekspertlari ma’no, gap tuzilishi, fazoviy bog‘lanish va qo‘lga bog‘liq bo‘lmagan belgilarni belgilaydi. Avatar qatlamida faqat mavjud yozuvni ishga tushirish bilan bu lingvistik vazifa bajarilgan hisoblanmaydi.

## 4. Ma’lumotlar va kelib chiqish talablari

**ASR to‘plami:** toza nutq, aksentli nutq, fon shovqini va uzunroq yozuvlar alohida qatlamlar bo‘lsin. Har yozuvda audio/video, davomiylik, foydalanish huquqi, original inson transkripti, segment/so‘z vaqtlari zarur bo‘lsa, shovqin turi va notiq identifikatori saqlanadi. Musiqa alohida eksperiment bo‘ladi. Sintetik demo real odam nutqining o‘rnini bosmaydi.

**ASL to‘plami:** dastlab pilot uchun 30–50 ta chegaralangan ta’limiy gap taklif etiladi. Bu hajm umumiy tarjima modelini o‘qitishga yetadi degani emas. Har gap uchun inglizcha ma’no, ASL ekspertining tarjima izohi, asl inson/animatsiya ijrosi, qo‘l va yuz belgilari, davomiylik, ijrochi, tekshiruvchi va versiya bog‘lanadi. Bir nechta tabiiy inglizcha variant bir niyatga mos kelishi mumkin; baholashda bunday oilalar orqali sizib chiqish nazorat qilinadi.

**Rozilik va huquqlar:** yangi yozuvda maqsad, saqlash muddati, kim ko‘rishi, ilmiy nashr va qayta tarqatish, mashinaviy o‘rganish uchun foydalanish hamda rozilikni qaytarish tartibi oldindan tushuntiriladi. Ijrochilar bilan rozilik va haq to‘lash shartlari kelishiladi. Tadqiqot identifikatorlari shaxsiy aloqa ma’lumotlaridan alohida saqlanadi; hisobotda foydalanuvchi identifikatori ochilmaydi. Ochiq arxivda fayl ko‘rinishi uning istalgan maqsad uchun ruxsatli ekanini o‘z-o‘zidan isbotlamaydi.

**Kelib chiqish manifesti:** source URL, litsenziya va uning olingan sanasi, commit/blob SHA, mahalliy SHA-256, ijrochi/rozilik ma’lumoti mavjudligi, eksport dasturi va versiyasi, yo‘qotilgan tracklar, tuzatishlar, tekshiruv va qaror sababi saqlansin. Studio Galt arxivi CC0 deb berilgan va tarjima sifati kafolatlanmaydi; [manbaning o‘z izohi](https://github.com/StudioGalt/Sign-Language-Mocap-Archive) professional tekshiruv zarurligini tushuntiradi. Hozirgi manifestda manba/blob SHA bor; bu to‘liq etik va reproduktiv ma’lumot kartasi emas.

**Ajratish:** o‘qitish, sozlash va yakuniy test qismlari oldindan muzlatiladi. Bir ijrochi/notiqning juda o‘xshash yozuvlari hamda bir gapning deyarli nusxalari bo‘linmalar orasida tarqalmasin. Faqat aniq lug‘atdan qaytarish baholanayotgan bo‘lsa, bu cheklov ochiq yozilsin; bundan yangi gaplarga umumlashtirish natijasi chiqarilmasin.

## 5. Baholash protokoli

| Qatlam | Metrika | Qanday olinadi |
|---|---|---|
| ASR | WER = (almashtirish + o‘chirish + qo‘shish) / tayanch so‘zlar; CER | Inson tayanch matni, oldindan belgilangan normallashtirish, yozuv va guruhlar kesimida |
| ASR to‘liqligi | O‘chirilgan so‘zlar ulushi, oxirgi/chegara so‘zlari xatosi | Uzoq audio va bo‘lak chegaralari belgilanadi; butun vaqt qayta ishlangani bilan adashtirilmaydi |
| Hisoblash | RTF = ishlov soniyalari / media soniyalari, yuklash va modelni ochish vaqti | Qurilma, model, oqimlar va sovuq/issiq boshlash alohida qayd etiladi |
| Lug‘at | Token qamrovi, missing/timing_review/unsupported_rig, tasdiqlangan va manba soni | Muzlatilgan matn/korpus versiyasi; ASL sifati sifatida talqin qilinmaydi |
| Vaqt | Inson belgilagan ishora boshlanishiga nisbatan mutlaq vaqt xatosi | Median, 95-persentil; aligned va estimated alohida |
| Avatar | Bog‘lanmagan track, NaN/cheksiz matritsa, qo‘lning kesishishi, eksport farqi | Avtomatik test + asl manba bilan ekspert vizual tekshiruvi |
| Lingvistik ijro | Ma’no, qo‘l shakli, yo‘nalish, fazoviylik, yuz belgisi, tabiiylik | Kamida ikki mustaqil ASL baholovchi; kelishuv va farqlarni hal qilish qaydi |
| Foydalanuvchi | Asosiy ma’no savollariga javob, vazifa muvaffaqiyati, vaqt va qulaylik | ASL foydalanuvchilari, oldindan tuzilgan savollar, pilotdan so‘ng muzlatilgan protokol |

Taqqoslashlar: (a) faqat subtitr, (b) subtitr + hozirgi lug‘at yordamchisi, (c) ekspert tasdiqlagan gap avatari; asl ekspert ASL ijrosi avatar yo‘qotishini ajratish uchun nazorat bo‘lishi mumkin. Bir xil kontentni takror ko‘rish natijani oshirmasligi uchun tartib va kontent muvozanatlanadi. ASL tajribasi va yozma inglizcha savodxonlik natijaga ta’sir qilishi mumkinligi qayd etiladi; savollar ham foydalanuvchiga qulay tilda beriladi.

Ishtirokchilar soni pilotdagi tarqoqlik va ilmiy rahbar bilan quvvat tahlilidan keyin belgilanadi; kichik qulay tanlanmadan butun karlar jamiyatiga xulosa chiqarilmaydi. Tajriba universitetning amaldagi tadqiqot tartibiga muvofiq tashkillashtiriladi. Natija manfiy yoki farqsiz bo‘lsa ham, xom anonim natijalar, cheklov va xatolar bilan yoziladi. Hozir ushbu foydalanuvchi tajribasining natijalari mavjud emas.

## 6. Bosqichlar va chiqish mezonlari

| Bosqich | Ish | Tugallanganini ko‘rsatuvchi dalil |
|---|---|---|
| M1 — barqaror lokal asos | Yuklash, ASR, tarix, subtitr, lug‘at holati va avatar xatolarini tekshirish | Avtomatik sinovlar va build o‘tgan; qo‘lda tekshirish qaydi; o‘rnatish yo‘riqnomasi |
| M2 — ma’lumotlar | Soha va gaplarni tanlash; ASL hamkorlari, huquq/rozilik, manifest, test bo‘linmasi | Muzlatilgan pilot korpus va ma’lumot kartasi; noma’lum huquqli yozuv ishlatilmagan |
| M3 — gap darajasidagi yechim | Tasdiqlangan gap/niyatni animatsiyaga bog‘lash; mos kelmasa tekshiruvga qaytarish | Har qabul qilingan gap uchun ASL ekspert qarori; ko‘r-ko‘rona so‘z almashtirishdan farqli aniq til qatlami |
| M4 — baholash | ASR, lug‘at, vaqt, eksport va foydalanuvchi tajribasi | Protokol, anonim jadval, xatolar tahlili va taqqoslashlar; o‘lchanmagan natija belgilanmagan |
| M5 — himoya paketi | Dissertatsiya matni, arxitektura, demo, kod/versiya, cheklovlar | Bitta qayta ishga tushiriladigan lokal paket; dalillarga mos xulosa va namoyish |

M1 bo‘yicha ishlar mavjud, lekin M2–M5 ni dastur kodi yozilgan deb tugallangan hisoblash mumkin emas. Amaldagi kodning `approved` holati haqiqiy til tekshiruvi hujjati bilan bog‘lanishi kerak.

## 7. Yakuniy qabul mezonlari loyihasi

Muhandislik mezonlari:

- Muzlatilgan versiyada `npm.cmd test`, `npm.cmd run build` va `node scripts/test-avatar.mjs` muvaffaqiyatli bajariladi; natija va muhit saqlanadi.
- Test to‘plamida noma’lum tokenlarning 100% i ochiq ko‘rsatiladi; kalibrlash va draft kliplari tasdiqlangan ASL sifatida ijro etilmaydi.
- Audit rejasida ruxsat etilmagan vaqt nisbati va qo‘llab-quvvatlanmaydigan rig alohida holat qaytaradi; subtitr va hisobot saqlanadi. Asosiy tezkor rejim lug‘at klipini ko‘pi bilan 1.25× ijro etadi va zarur pauzani qo‘shadi; noma’lum so‘z qo‘shimcha hold bermaydi. Ixtiyoriy harflashda to‘liq tabiiy davomiylik saqlanadi. Tezlik/vaqt xaritasi texnik tekshiriladi; tushunarlilik alohida baholanadi.
- Qayta tahrirlangan matn eski so‘z vaqti yoki auditini ishonchli deb ko‘rsatmaydi.
- Texnik animatsiya sinovida bog‘lanmagan track va cheksiz matritsa yo‘q; eksportdagi o‘zgarishlar qayd etiladi.

Ilmiy mezonlar uchun boshlang‘ich taklif: toza, cheklangan sohadagi real nutqda WER ≤15%; ekspert baholagan qabul korpusida tuzatilmagan jiddiy ma’no xatosi 0; ishonchli tekislangan namunalarda ishora boshlanishining 95-persentil mutlaq xatosi ≤150 ms; foydalanuvchi tajribasida asosiy ma’no savollarining kamida 80% i to‘g‘ri. Bu raqamlar hozirgi dastur natijalari yoki universal standart emas. Pilotdan oldin asoslantirish/tasdiqlash talab etiladi; keyin natijaga qarab mezonni pasaytirish o‘rniga bajarilmagan mezon ochiq qayd etiladi. Shovqin va aksent kesimidagi natijalar alohida beriladi.

Korpusning 100% lug‘at qamrovi, chiroyli avatar, testlarning o‘tishi yoki bitta sintetik namunadagi 0 WER umumiy tarjimon tayyorligini isbotlamaydi. Mahsulot “cheklangan ta’limiy soha uchun baholangan ASL platformasi” deb taqdim etilishi uchun M2–M4 dalillari ham kerak.

## 8. Dissertatsiyaga kiritiladigan dalillar

1. Muammo, foydalanuvchi ehtiyoji, ASL tanlovi, soha va mavjud yondashuvlar.
2. Modullar, ma’lumotlar sxemasi, ASR bo‘lak algoritmi, bilimlar bazasi va holat qoidalari.
3. Dataset kartasi, kelib chiqish/rozilik, bo‘linmalar va mutaxassis protokoli.
4. Eksperiment sozlamalari, baseline, metrikalar, natijalar va xatolar tahlili.
5. Foydalanuvchi tushunarliligi, amaliy cheklovlar, takrorlash yo‘riqnomasi va keyingi yo‘nalish.

Texnik va model tekshiruvi yozuvlari [VALIDATION.md](VALIDATION.md) da saqlanadi. Tarixiy o‘lchov, yangi tajriba va kelajak maqsadi matnda bir-biridan aniq ajratiladi.
