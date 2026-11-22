# SignBridge UZ MetaHuman ayol tarjimon

Tanlov sanasi 2026-10-30. Foydalanuvchi MetaHuman orqali yangi ayol qiyofasi yaratishni tanladi. Rocketbox modeli asosiy yo‘nalish sifatida tanlanmadi.

## Qiyofa va kadr

Foydalanuvchi bergan birinchi rasm sifat mezoni: tabiiy inson nisbatlari, realistik teri va ko‘zlar, tartibli orqaga yig‘ilgan soch, sodda qora kalta yengli kiyim. Shaxsning aynan yuzini ko‘chirish talab qilinmaydi. Kadr beldan yuqori, ikkala tirsak va barcha barmoq uchlari ishora davomida ko‘rinadi. Yuz va qo‘llar bir tekis yoritiladi. Ijro ishora ma’nosiga mos kelmagan tasodifiy bosh/og‘iz/qo‘l harakatlari bilan to‘ldirilmaydi.

## Muhit tekshiruvi

AMD Radeon integratsiyalashgan GPU; WMI AdapterRAM 512 MiB deb ko‘rsatadi, bu umumiy shared GPU xotira limiti emas. Tizim RAM 23.4 GiB. C disk bo‘sh 654.0 GiB, D disk 474.1 GiB. Epic Games Launcher va Unreal standart o‘rnatish yo‘llarida topilmadi. MetaHuman ishlashi yoki render tezligi hali tekshirilmagan.

## Tayyorlash tartibi

1. Epic Games Launcher va Unreal Engine mos versiyasi o‘rnatiladi. Epic kirishi hamda litsenziya shartlarini qabul qilish zarur bo‘lsa, foydalanuvchi o‘zi yakunlaydi. MetaHuman Creator Core Data komponenti tanlanadi va loyihada MetaHuman Creator plagini yoqiladi.
2. Ayol MetaHuman qiyofasi yaratiladi, beldan yuqori sinov kadrida ko‘rib chiqiladi. Yuqori sifat uchun mavjud integratsiyalashgan GPU yetarliligi sinov bilan aniqlanadi; mos GPU qurilmada bir marta render qilish muqobil yo‘l.
3. Ruxsatli SignAvatars 3D annotatsiyalari olingach, tana va barmoqlar harakati MetaHuman skeletiga retarget qilinadi. Yuz koeffitsiyentlari alohida kalibrlanadi.
4. Dastlab 5–10 ibora oldindan render qilinib mavjud FastAPI/React/FFmpeg yo‘liga ulanadi. Qiyofa tayyorligi ishora to‘g‘riligini isbotlamaydi.

MetaHuman qiyofasi hozir yaratilmagan. Katta Unreal yuklamasi boshlanmagan. Ishchi platforma haqiqiy How2Sign inson videolari bilan saqlangan.

Rasmiy o‘rnatish manbasi: https://dev.epicgames.com/documentation/en-us/metahuman/getting-started-with-metahuman-creator
