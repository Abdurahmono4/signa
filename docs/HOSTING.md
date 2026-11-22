# Vercel va Netlify

Holat: deploy hali bajarilmagan. GitHub profili: Abdurahmono4.

React frontend statik hostingga chiqariladi. Python, Whisper, MaDiS, FFmpeg,
model fayllari va foydalanuvchi videolari alohida backendda qoladi.
Vite development proxy production buildda ishlamaydi.

## Tayyorlash

1. Backend uchun ommaviy HTTPS manzil tayyorlang. /api/health javobini tekshiring.
   Ommaviy kirishdan avval ishlar va fayllarga kirish nazoratini sozlang.
2. Repozitoriy ildizida quyidagini haqiqiy backend manzili bilan ishga tushiring:

   node scripts/configure-hosting.mjs https://YOUR-BACKEND-HOST

3. npm ci --prefix frontend
4. npm run build --prefix frontend
5. Yangi private GitHub repozitoriyga tekshirilgan kodni yuklang.
   datasets, storage, audio, model vaznlari, .venv, tools va maxfiy fayllarni yuklamang.
   Uchinchi tomon avatar/model materiallari litsenziyasini alohida tekshiring.
6. Vercel va Netlify'da repozitoriyni import qiling. Root/base directory repozitoriy ildizi.
   Generatsiya qilingan vercel.json va netlify.toml build va proxy sozlamalarini beradi.

Faqat /api va /assets/avatars backendga yo'naltiriladi. Vite buildning o'z
/assets/*.js va CSS fayllari hostingdan beriladi.

## Qabul sinovi

- Ikkala hosting URL orqali sahifa, /api/health va avatar GLB ochilishi.
- Yangi inglizcha audio/video yuklash, transkripsiya, avatar va MP4 yuklab olish.
- Katta uploadlar, uzoq so'rovlar va MP4 Range so'rovlarini hosting proxy
  cheklovlari bilan alohida tekshirish; faqat build o'tishi butun tizim ishlashini isbotlamaydi.
- Noutbuk backend bo'lsa, noutbuk va tunnel o'chganda generatsiya ishlamaydi.
- signbridge.uz xarid qilinmaguncha unga deploy qilingan deb hisoblamang.
