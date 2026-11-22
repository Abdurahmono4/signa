# Amaldagi avatar pipeline

2026-11-02: asosiy avatar Rocketbox Female 01; MaDiS SMPL-X harakati Three.js skeletal kliplarga moslanadi, pauzada relaxed-idle qo‘llanadi. Asosiy eksport 1024×768 shaffof PNG → FFmpeg side-by-side/markaziy audio video → ASS subtitr → H.264/AAC MP4. Tafsilot va real sinov chegaralari: [OUTPUT_QUALITY.md](OUTPUT_QUALITY.md).

Quyidagi qayd dastlabki legacy importer haqida tarixiy ma’lumot; hozirgi asosiy avatar qiyofasi emas.

# Avatar va eksport

`assets/avatars/galtis.glb` — CC0 Studio Galt skeletli modeli. `frontend/src/interpreter.ts` lokal Signa loyihasidan saqlangan tashqi ko‘rinish moslamalari; original manba o‘zgartirilmadi. `demo-asl-hello.json` — manba ASL harakat yozuvi, lingvistik tasdiqsiz texnik namuna.

Browser preview: 384×512 tuval, shaffof fon, beldan yuqori yaqin kamera. GLB suyaklari va AnimationClip trek nomlari mos bo‘lishi zarur. Importer mavjud rig tugunlarini, animatsiya vaqtini, o‘lchamini va sonli qiymatlarni tekshiradi. Yangi avatar rigini avtomatik retarget qilish qo‘llanmaydi. Yangi harakat Blenderda ushbu rigga retarget qilinib Three.js AnimationClip JSON sifatida chiqarilishi kerak. Max 30 soniya / 8 MB.

Kadr eksporti: deterministic vaqt sampling → shaffof PNG → backend → FFmpeg overlay. Avatar kengligi 20–45%, chap/o‘ng pastki burchak. 720p va 1080p, H.264 yuv420p, AAC 160k, faststart. Audio-only faylga navy fon yaratiladi. Subtitr SRT dan FFmpeg orqali kuydiriladi. MP4 real fayl bo‘lgachgina download ochiladi.

Brauzerni kadrlar yuklanishi tugamaguncha ochiq qoldiring. Uzoq kontent ko‘p PNG so‘rovi va vaqt talab qiladi. Fon navbati keyin MP4 ni yig‘adi. Bu hali server GPU/offline render farm emas.

Animatsiya vaqti ibora oralig‘iga chiziqli moslanadi; juda tez gaplarda ishoraning o‘qilishi kafolatlanmagan. Silliq fonetik o‘tish va yuzning lingvistik markerlari hali alohida tekshiruv talab qiladi.
