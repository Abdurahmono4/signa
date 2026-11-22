# SignBridge UZ tabiiy tarjimon sifati va amalga oshirish rejasi

Sana: 2026-10-30. Maqsad: foydalanuvchi ko‘rsatgan SignAvatar darajasiga yaqin inson qiyofasi va tushunarli harakat uchun tekshiriladigan bosqichlar. Mukammal tarjima kafolati berilmaydi.

## Nimalar tasdiqlandi

1. SignAvatar.org asoschisi 2023-yilgi intervyuda Unreal Engine MetaHuman va NLP/ML ishlatilganini aytgan. Bu tarixiy texnologik dalil; hozirgi barcha ichki komponentlar yoki model versiyalari ochiq emas.
   https://www.netokracija.rs/signavatar-206294
2. Kompaniyaning 2023 taqdimoti nutq → matn → glossa → avatar va Transformer yondashuvini ko‘rsatadi. Bu tayyor API yoki yuklanadigan checkpoint emas.
   https://interoperable-europe.ec.europa.eu/sites/default/files/document/2023-10/PitchDeck%20SignAvatar.pdf
3. Serbiya Innovation Fund 2025-07-27 dagi loyiha bayonida kar ijrochilarning motion capture kiyimlarida yozilgan harakatlari 3D avatarga o‘tkazilishini tushuntirgan. Kiyim brendi, aniq model arxitekturasi va avatarlarni tijorat mahsulotidan olish sharti aniqlanmadi.
   https://www.inovacionifond.rs/lat/info/putujte-sa-signavatar-informacije-u-aplikaciji-srbijavoz-i-na-znakovnom-jeziku
4. ZhengdiYu/SignAvatars — boshqa tashkilotlarning ECCV 2024 tadqiqoti. SMPL-X/MANO annotatsiyalari va viewer bor. Uning texnik rangli meshi tayyor fotorealistik avatar emas. 182-parametrli harakatni mavjud MaDiS 133-parametrli oqimga teng deb bo‘lmaydi.
   https://github.com/ZhengdiYu/SignAvatars
5. MetaHuman Creator zamonaviy versiyalarda Unreal Engine ichida ishlaydi; yuz, soch, kiyim va materiallar hamda rig alohida aktivlar sifatida tayyorlanadi.
   https://dev.epicgames.com/documentation/metahuman/metahuman-creator-in-unreal-engine

## Hozir bajarilgan texnik yaxshilanish

Inson videosi eksportiga native FFmpeg yo‘li qo‘shildi. Frontend render/start so‘rovida native_human=true yuboradi. 24 tagacha ijro bo‘lagi bo‘lsa server kliplarni asl videodan bevosita kesib, vaqtga moslab, 24 fps MP4 ga yig‘adi. Brauzer PNG capture va yuklash talab qilinmaydi. Ko‘proq bo‘laklarda mavjud PNG yo‘li saqlanadi; shuning uchun barcha uzun videolar tezlashadi degan da’vo yo‘q.

Tarjimon mavjud intervaldagina ko‘rsatiladi. Asl audio, subtitr va manba/litsenziya metadata saqlanadi. Yashil fon qoidasi brauzerdagi rang farqi asosidagi alfa bilan moslashtirildi. Bu yashil kiyim yoki yoritishning barcha holatlarida mukammal segmentatsiya degani emas.

Preview tanlangan overlay/yonma-yon, tarjimon kengligi va chap/o‘ng holatini ko‘rsatadi. Eski natijani brauzer keshidan ko‘rsatmaslik uchun result token URL ga qo‘shilgan.

Haqiqiy mahalliy namuna: LOCAL_ID. 2.239093 s, 1280×720, H.264/AAC, 24 fps. Native eksport PNG yuklamasiz bajarildi. Yashil fonni tozalash bilan bitta o‘lchov 11.41 s; tezlik umumiy benchmark emas. Natija examples/native-human-2026-10-30.mp4.

## Eng sodda tabiiy 3D yo‘li

Jonli Unreal serveri yoki Pixel Streamingni hozir majburiy qilish o‘rniga, kichik iboralar kutubxonasini oldindan sifatli render qilish tavsiya etiladi. React shu videolarni hozirgi HumanSigner oqimi kabi sinxron ijro etadi, FastAPI va FFmpeg esa audio/video natijani yig‘adi. Bu muhandislik taklifi, SignAvatar aynan shunday ishlaydi degan tasdiq emas.

### Bosqich 1 mavjud inson videosini sifat mezoni sifatida saqlash

Holat: bajarilgan. Mos iboralar inson videosida ijro etiladi; mos bo‘lmagan gapda subtitr ko‘rsatiladi. 3D harakatlar asosiy foydalanuvchi oqimiga avtomatik qaytarilmaydi.

### Bosqich 2 kichik 3D namuna resurslarini olish

Holat: kutilmoqda. SignAvatars rasmiy shakli orqali 5–10 ta mahalliy klipga mos SMPL-X annotatsiyasi va ruxsat shartlari olinadi. Epic/MetaHuman qiyofasi yoki boshqa qonuniy, barmoqli, yuz rigli inson modeli alohida olinadi. Hozir ariza yuborilmadi, litsenziya qabul qilinmadi va katta download qilinmadi.

To‘liq How2Sign RGB yuklanishi 3D annotatsiyalarga ruxsat o‘rnini bosmaydi. Ruxsat etilgan SMPL-X/MANO model aktivlari ham alohida kerak. Hozirgi validation to‘plami rivojlantirishda ishlatilgan; yakuniy ilmiy test sifatida qayta ishlatilmaydi.

### Bosqich 3 harakatni anatomik moslashtirish

Holat: bajarilmagan. SMPL-X root/tana/bilak/barmoq kanallari yangi rigga retarget qilinadi; bind pose va o‘qlar tekshiriladi. Qo‘lning boshlang‘ich shakli hisobga olinadi. SMPL-X yuz koeffitsiyentlari MetaHuman yuz boshqaruvlariga tayyor 1:1 xarita emas; soxta tabassum, bosh harakati yoki gapirish animatsiyasi ishora grammatikasi o‘rnini bosmaydi.

Qabul mezoni: manba bilan yonma-yon ko‘rishda barmoq shakli, qo‘l yo‘nalishi, ishora joyi, yuz belgisi, timing va qo‘llarning kesilmasligi alohida ko‘riladi; so‘ng ASL mutaxassisi baholaydi.

### Bosqich 4 bir marta render va platformaga integratsiya

Holat: render aktivlari yo‘q. Unreal/MetaHuman qiyofasida beldan yuqori 5–10 ibora oldindan render qilinadi. Kadr, FPS, davomiylik, ibora ID, til, manba, litsenziya va ekspert holati bilan saqlanadi. Keyin mavjud klip rejasiga ulanadi. Unreal dasturini brauzer ichida Three.js GLB sifatida avtomatik ishga tushirish mumkin deb qaralmaydi.

### Bosqich 5 miqyos va ilmiy baholash

Holat: keyingi ish. Ruxsatli training qismi, mustaqil test qismi, mutaxassis bahosi va tezlik/xotira o‘lchovi tashkil etiladi. To‘liq datasetni katalogga joylash modelni o‘qitish degani emas. Dataset importi, parametr tayyorlash, training va haqiqiy tarjima sifati to‘rtta alohida natija sifatida qayd qilinadi.

## Uskuna chegarasi

Hozirgi Ryzen 9, 24 GB RAM, AMD integratsiyalashgan GPU mashinasida mavjud CPU pipeline ishlaydi. MetaHuman yuqori sifatli authoring/renderi bu mashinada sinovdan o‘tkazilmadi; ravon ishlashi kafolatlanmaydi. Og‘ir qiyofani mos GPU qurilmada bir marta render qilib, tayyor videoni shu kompyuterda ishlatish eng yengil variantdir. Pulli server yoki yangi uskuna xaridi amalga oshirilmadi.

Pixel Streaming kelajakdagi variant: Epic NVENC, AMD AMF yoki VideoToolbox mos encoder apparatini talab qiladi. AMD integratsiyalashgan GPU borligi o‘zi barcha talablarga moslikni isbotlamaydi.
https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-pixel-streaming-reference

## Nimani tayyor deb bo‘lmaydi

Fotorealistik 3D qiyofa, MetaHuman importi, SMPL-X retargeti, erkin gaplar uchun mukammal tarjima, yangi model trainingi va O‘zbekiston imo-ishorasi hali bajarilmagan. Hozirgi MP4 dagi inson — haqiqiy manba videosi, yangi yaratilgan 3D avatar emas.
