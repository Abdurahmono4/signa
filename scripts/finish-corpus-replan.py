from pathlib import Path
p=Path('frontend/src/main.tsx');s=p.read_text(encoding='utf-8')
s=s.replace('>MP4 video yaratish</button>', '>MP4 video yaratish</button><button disabled={!job.translation} onClick={async()=>{try{setJob(await api<Job>(`/jobs/${job.id}/replan`,json({})))}catch(e){setError(String(e))}}}>Qamrovni yangilash</button>')
s=s.replace('Ushbu datasetda qayta o‘qitilmadi.', 'Ushbu datasetda qayta o‘qitilmadi. Uzun faylda CPU hisoblashi video davomiyligidan ancha uzoq bo‘lishi mumkin; jarayonni bekor qilish mumkin.')
p.write_text(s,encoding='utf-8')
