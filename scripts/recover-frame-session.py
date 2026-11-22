from pathlib import Path
p=Path('frontend/src/main.tsx');s=p.read_text(encoding='utf-8').replace("['queued','processing','rendering']", "['queued','processing','rendering','frames']");p.write_text(s,encoding='utf-8')
