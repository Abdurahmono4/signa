> 2026-11-01 amaldagi oqim: public inglizcha input, Whisper small CPU INT8, MaDiS alohida CPU inference, Rocketbox Female 01 GLB, 512×384 RGBA brauzer kadri / 24 fps, FFmpeg 720p H.264/AAC. How2Sign native inson eksporti ichki vositalarda alohida qolgan. Matn lug‘ati preflight va qisman caption-only interval qo‘llanadi. Quyidagi boshlang‘ich arxitektura bayoni tarixiy; hozirgi API va cheklovlar uchun README.md, PARTIAL_MOTION.md, CURRENT_STATUS.md ustuvor.

# Arxitektura

React + TypeScript + Vite + Tailwind CSS → mahalliy FastAPI → SQLite.
Nutq: Faster-Whisper, multilingual model, language=uz, CPU INT8, VAD kesishsiz, so‘z vaqt belgilari.
Tarjima: `backend/app/translation.py` ichidagi `translate(text, timestamps, signs)`.
Avatar: React Three Fiber, Three.js, GLB skelet + AnimationMixer, individual barmoqlar va mavjud yuz morph kanallari.

Oqim: POST upload → POST jobs → fon ishchisi/ASR → tekshirilgan iboralar → brauzerda 384×512 shaffof PNG kadrlar (12 fps) → FFmpeg kompozitsiya → H.264/AAC MP4 → FFprobe → download.
Original audio qayta kodlanadi (AAC); mazmuni original, bit-identik emas. Video 16:9 720p/1080p tuvalga proporsional joylanadi. Eksportda audio/video boshlanishi bir vaqtga tayangan; noodatiy manba PTS fayllari alohida sinov talab qiladi.

Backend bitta worker navbatidan foydalanadi, bir vaqtda og‘ir CPU vazifalari yig‘ilmaydi. Job holati SQLite da saqlanadi. Server uzilganda tugallanmagan fon vazifalar failed holatiga o‘tadi. Cancel model yuklash va Whisper joriy segmenti tugashini kutishi mumkin. FFmpeg progress oqimida bekor qilinadi. Eksportdan keyin vaqtinchalik PNG lar o‘chiriladi, original fayllar saqlanadi.

Mahalliy portlar 5174/8001: oldingi Signa 5173/8000 ishlayotganligi uchun uning serverlari to‘xtatilmadi. Bir foydalanuvchili lokal prototip; autentifikatsiyasiz internetga chiqarilmasin. Faqat 127.0.0.1 ga bind.

Kelgusida: API modullarini alohida routerlarga ajratish, navbat xizmati, server render worker, dataset versiyalash, lingvistik qoidalar, baholangan neyron model adapteri.
