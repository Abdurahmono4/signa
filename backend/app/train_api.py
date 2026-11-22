"""Local train phrase retrieval, not training or independent evaluation."""
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from . import how2sign,train_catalog
router=APIRouter(prefix='/api/how2sign/train')

@router.get('/status')
def status():return train_catalog.status(how2sign.BASE)

@router.get('/clips/{ident}')
def clip(ident:str):
    try:record=how2sign.resolve_record(ident)
    except (ValueError,OSError):raise HTTPException(404,'Train klipi ochilmadi.')
    if not record or record.get('split')!='train':raise HTTPException(404,'Train klipi topilmadi.')
    return FileResponse(how2sign.resolve_clip(ident),media_type='video/mp4')
