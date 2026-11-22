# Model matni va foydalanuvchi tuzatishi

## 2026-11-01 topilgan sabab

Oldingi qisman sinovda `In order to obtain that,` iborasi tokenizerga mos emas deb qaytgan. Tekshiruv uning so‘zlari emas, runnerning terminal tinish belgisi qoidasi muammo ekanini ko‘rsatdi: oxirida vergul bo‘lgan matnga nuqta qo‘shilib `,.` tokeni hosil bo‘lgan. Ushbu token compact lug‘atda yo‘q. Vergulni gap yakunidagi nuqtaga aylantirgan model kirishi esa lug‘atga mos.

Bu ilgari “lug‘atda qo‘llanmaydigan ibora” deb yozilgan xulosani aniqlashtiradi. V4 dagi qisman hisobot tarixiy haqiqiy natija, ammo ushbu konkret ibora haqiqiy so‘z yetishmasligi holati emas.

## Tuzatish

`backend/app/neural_text.py::model_caption` modelga yuboriladigan matnning oxiridagi vergul/nuqtali vergul/ikki nuqtani yakuniy nuqta bilan almashtiradi; ichki tinish belgisi, so‘zlar va tartib saqlanadi. Preflight va runner request aynan shu funksiyadan foydalanadi. Asl transkript, vaqtlar va MP4 subtitrlari o‘zgartirilmaydi. Foydalanuvchining nutqi modelga moslash uchun qayta yozilmaydi.

Cache versiyasi `signa-madis-plan-v5-model-punctuation`. Oldingi motion/MP4lar o‘chirilmaydi; yangi so‘rov yangi kalitda tekshiriladi. Qisman fallback haqiqatan mos kelmaydigan iboralar uchun qoladi; tasdiqlangan ASL aniqligi deb ko‘rsatilmaydi.

## Interfeys

Xato yoki qisman natijada «Nutq matnini tekshirish» tugmasi bor. U bosilmaguncha transkript formasi ochilmaydi. Faqat audioda eshitilgan xatolarni tuzatish tavsiya etiladi. Saqlash eski revisionni bosib yubormaydi, source vaqtlar o‘zgarmaydi; matn o‘zgarsa avatar qayta tayyorlanadi, oldingi MP4 aniq token bilan tarixda saqlanadi.

Work brauzer boshqaruvi user tomonidan yoqilgan deb bildirilgan, ammo tool qayta ulanishdan keyin ham disabled javobini qaytargan. Shu sabab ushbu yangi boshqaruv va uzun videoning yangi 3D MP4 eksporti brauzerda hali tasdiqlanmagan. TypeScript/Vite build, backend edit/revision testlari o‘tgan.
